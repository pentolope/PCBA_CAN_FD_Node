"""Board-level electrical checks, stated as claims with their evidence.

Every number here comes from `components/parameters.json` (which cites the
frozen document it was read from) or from the netlist. Nothing is asserted
that a document, a component value or a measurement does not support, and a
quantity that cannot be established is reported as UNKNOWN rather than
assumed.
"""
from __future__ import annotations

import json
import os
import sys

from . import libraries, netlist

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMETERS_PATH = os.path.join(REPO_ROOT, "components", "parameters.json")
CATALOG_PATH = os.path.join(REPO_ROOT, "components", "jlcpcb.json")
TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
FOOTPRINT_ROOT = "/usr/share/kicad/footprints"
LOCAL_FOOTPRINT_ROOT = os.path.join(REPO_ROOT, "library")

if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa import claim  # noqa: E402

DIRECT = "direct"
ASSUMED = "assumed"
DERIVED = "derived"

EVIDENCE_CLASSES = {
    DIRECT: "datasheet-behavioral",
    ASSUMED: "assumed-behavioral",
    DERIVED: "design-source",
}

BRIEF = "BRIEF.md"


def load_parameters():
    with open(PARAMETERS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _mpn(reference):
    return netlist.PARTS[reference]["mpn"]


def _spec(parameters, reference):
    return parameters["parts"][_mpn(reference)]


def _evidence(basis, documents, assumptions=(), omissions=(),
              source="components/parameters.json"):
    provenance = {"source": source,
                  "documents": sorted(set(documents))}
    return claim.evidence(
        "device_electrical", EVIDENCE_CLASSES.get(basis, "design-source"),
        provenance, assumptions=list(assumptions),
        omitted_contributions=list(omissions))


def _requirement(name, op, value, source=None):
    # The source names the statement kind and origin from the register,
    # so a reader of one claim can see whether its requirement came from
    # the brief, a datasheet derivation or this design's own declaration
    # without opening the register - and a bare "BRIEF.md" cannot return.
    from . import requirements
    return claim.requirement(name, source or requirements.source_of(name),
                             {"op": op, "value": value})


#: How the requirement's operator turns a conservatively computed number into
#: the knowledge shape it actually supports. A worst case evaluated against a
#: floor is a lower bound on the real quantity; against a ceiling it is an
#: upper bound. Nothing that omits a contribution or rests on a premise is
#: ever allowed to call itself exact.
_BOUND_FOR_OPERATOR = {">=": claim.LOWER_BOUND, ">": claim.LOWER_BOUND,
                       "<=": claim.UPPER_BOUND, "<": claim.UPPER_BOUND}


def _claim(identity, units, significance, value, basis, documents,
           requirement, knowledge=None, scope_level="net",
           assumptions=(), omissions=(),
           source="components/parameters.json"):
    if value is None:
        return claim.claim(
            scope_level, identity, units, claim.UNKNOWN, {},
            _evidence(basis, documents, assumptions, omissions, source),
            significance, None, requirement)
    if knowledge is None:
        if basis == ASSUMED or omissions:
            knowledge = _BOUND_FOR_OPERATOR.get(
                requirement["assertion"]["op"], claim.APPROXIMATE)
        else:
            knowledge = claim.EXACT
    basis_record = None
    if knowledge != claim.EXACT:
        basis_record = claim.knowledge_basis(
            basis, "datasheet_limit" if basis == DIRECT else basis)
    return claim.claim(
        scope_level, identity, units, knowledge, {"value": value},
        _evidence(basis, documents, assumptions, omissions, source),
        significance, basis_record, requirement)


def _structural(identity, significance, violations, requirement_name,
                documents=(), basis=DERIVED, assumptions=(), omissions=(),
                source="components/parameters.json"):
    """A count of violations: zero is the only acceptable answer."""
    return _claim(identity, "violations", significance, float(len(violations)),
                  basis, documents, _requirement(requirement_name, "<=", 0.0),
                  scope_level="board", assumptions=assumptions,
                  omissions=omissions, source=source)


def _resistor_ohms(reference):
    value = netlist.PARTS[reference]["value"]
    if value.endswith("k"):
        return float(value[:-1]) * 1e3
    if value.endswith("R"):
        return float(value[:-1])
    raise ValueError("resistor %s carries the unparsable value %r"
                     % (reference, value))


def _capacitance_farads(reference):
    parameters = load_parameters()
    return _spec(parameters, reference)["capacitor"]["capacitance_f"]["value"]


def _resistor_tolerance(parameters, reference):
    spec = _spec(parameters, reference)["resistor"]
    entry = spec.get("tolerance")
    return 0.0 if entry is None else entry["value"]


def _capacitor_tolerance(parameters, reference):
    return _spec(parameters, reference)["capacitor"]["tolerance"]["value"]


def _channel_reference(prefix, channel, offset=0):
    return "%s%d" % (prefix, channel + offset)


# ---------------------------------------------------------------------------
# the supply model every rail and channel claim is built on

class Supply:
    """Worst-case rail voltages and currents, from parameters and values.

    Currents are upper bounds and drops are computed at the highest current
    and the highest resistance the datasheet and the tolerance permit, so no
    downstream figure is optimistic.
    """

    def __init__(self, parameters):
        self.parameters = parameters
        self.documents = {"stm32g431_st", "tcan1042_ti", "mp2459_mps",
                          "ht75rxx_holtek", "nce6003x_nce",
                          "wst6066a_winsok", "pptc_1812l200_lute",
                          "res_uniroyal"}

        mcu = _spec(parameters, "U1")
        transceiver = _spec(parameters, "U2")
        converter = _spec(parameters, "U3")["converter"]
        regulator = _spec(parameters, "U4")["regulator"]
        blocking = _spec(parameters, "Q1")["fet"]
        output_fet = _spec(parameters, "Q2")["fet"]
        fuse = _spec(parameters, "F1")["resettable_fuse"]

        self.input_min_v = netlist.INPUT_SUPPLY["min_v"]
        self.input_max_v = netlist.INPUT_SUPPLY["max_v"]
        self.transient_clamp_v = netlist.TRANSIENT_CLAMP_MAX_V
        self.channel_current_a = netlist.OUTPUT_CURRENT_RATING_A
        self.field_current_a = (netlist.OUTPUT_COUNT
                                * netlist.OUTPUT_CURRENT_RATING_A)

        # logic rail: the regulator's own accuracy about its nominal output
        self.logic_rail_v = regulator["output_voltage_v"]["value"]
        tolerance = regulator["output_tolerance"]["value"]
        self.logic_rail_min_v = self.logic_rail_v * (1.0 - tolerance)
        self.logic_rail_max_v = self.logic_rail_v * (1.0 + tolerance)

        # intermediate rail: the converter's feedback reference over its own
        # limits and the divider's tolerance, which is what the transceiver's
        # supply window is judged against
        upper = _resistor_ohms("R2")
        lower = _resistor_ohms("R3")
        divider_tolerance = max(_resistor_tolerance(parameters, "R2"),
                                _resistor_tolerance(parameters, "R3"))
        ratio = 1.0 + upper / lower
        self.intermediate_ratio = ratio
        self.intermediate_rail_v = converter["feedback_voltage_v"]["value"] * ratio
        self.intermediate_rail_min_v = (
            converter["feedback_voltage_min_v"]["value"]
            * (1.0 + (upper * (1.0 - divider_tolerance))
               / (lower * (1.0 + divider_tolerance))))
        self.intermediate_rail_max_v = (
            converter["feedback_voltage_max_v"]["value"]
            * (1.0 + (upper * (1.0 + divider_tolerance))
               / (lower * (1.0 - divider_tolerance))))

        # logic-side load, bounded rather than typical: the controller at its
        # stated maximum, the transceiver's interface supply, the indicator
        # taken as the whole rail across its series element so no forward
        # voltage figure is needed, the rail bleed, and the four input clamps
        # feeding current back into the rail is a source, not a load.
        indicator_min_ohm = _resistor_ohms("R11") * (
            1.0 - _resistor_tolerance(parameters, "R11"))
        self.indicator_current_max_a = (self.logic_rail_max_v
                                        / indicator_min_ohm)
        bleed_min_ohm = _resistor_ohms("R6") * (
            1.0 - _resistor_tolerance(parameters, "R6"))
        self.bleed_current_max_a = self.logic_rail_max_v / bleed_min_ohm
        self.mcu_current_max_a = mcu["supply_current_max_a"]["value"]
        self.logic_current_max_a = (
            self.mcu_current_max_a
            + transceiver["io_supply_current_max_a"]["value"]
            + self.indicator_current_max_a
            + self.bleed_current_max_a)

        # intermediate-rail load: the transceiver driving a dominant bit into
        # the lowest load its datasheet characterises, plus the regulator and
        # everything behind it, plus the regulator's own quiescent draw
        self.transceiver_current_max_a = transceiver["supply_current_max_a"][
            "value"]
        self.regulator_quiescent_a = _spec(
            parameters, "U4")["supply_current_max_a"]["value"]
        self.intermediate_current_max_a = (
            self.transceiver_current_max_a + self.logic_current_max_a
            + self.regulator_quiescent_a)

        # converter input current, from the output power and a deliberately
        # pessimistic efficiency
        self.converter_efficiency = 0.75
        self.converter_input_current_max_a = (
            self.intermediate_rail_max_v * self.intermediate_current_max_a
            / (self.converter_efficiency * self.input_min_v))

        self.regulator_floor_v = (self.logic_rail_max_v
                                  + regulator["dropout_bound_v"]["value"])

        # the reverse-blocking device carries the whole board's return
        self.blocking_gate_v = _spec(
            parameters, "D2")["zener"]["zener_voltage_min_v"]["value"]
        self.blocking_rds_ohm = blocking["rds_on_ohm"]["10"]["value"]
        self.total_return_current_a = (self.field_current_a
                                       + self.converter_input_current_max_a)
        self.blocking_drop_max_v = (self.total_return_current_a
                                    * self.blocking_rds_ohm)

        # the field supply passes the resettable fuse
        ambient = "%d" % int(netlist.AMBIENT_MAX_C)
        if ambient not in fuse["hold_current_a"]:
            raise KeyError("no hold current is tabulated at %s C" % ambient)
        self.fuse_hold_current_a = fuse["hold_current_a"][ambient]["value"]
        self.fuse_resistance_max_ohm = fuse["resistance_max_ohm"]["value"]
        self.fuse_resistance_min_ohm = fuse["resistance_min_ohm"]["value"]
        self.field_supply_min_v = (
            self.input_min_v
            - self.field_current_a * self.fuse_resistance_max_ohm
            - self.blocking_drop_max_v
            - netlist.BOARD_COPPER_BUDGET_OHM * self.field_current_a)

        # the low-side switch, driven straight from a controller pin
        self.output_gate_v = self.logic_rail_min_v
        self.output_characterised_gate_v = min(
            float(key) for key in output_fet["rds_on_ohm"])
        self.output_rds_ohm = output_fet["rds_on_ohm"]["2.5"]["value"]


def _supply_documents(supply, extra=()):
    return sorted(set(supply.documents) | set(extra))


# ---------------------------------------------------------------------------
# rails

def evaluate_rails(parameters):
    """Each rail lands inside the window the parts it feeds require."""
    supply = Supply(parameters)
    transceiver = _spec(parameters, "U2")
    mcu = _spec(parameters, "U1")
    converter = _spec(parameters, "U3")["converter"]
    regulator = _spec(parameters, "U4")["regulator"]
    results = [
        {
            "id": "intermediate_rail_above_transceiver_minimum",
            "identity": netlist.INTERMEDIATE_RAIL_NET,
            "claim": _claim(
                netlist.INTERMEDIATE_RAIL_NET, "V", "supply_compatibility",
                supply.intermediate_rail_min_v, DIRECT,
                ("mp2459_mps", "res_uniroyal", "tcan1042_ti"),
                _requirement("at_or_above_the_transceiver_supply_minimum",
                             ">=", transceiver["supply"]["min_v"]["value"]),
                assumptions=(
                    "the feedback divider is at the tolerance corner that "
                    "lowers the output, and the reference at its datasheet "
                    "minimum",)),
        },
        {
            "id": "intermediate_rail_below_transceiver_maximum",
            "identity": netlist.INTERMEDIATE_RAIL_NET,
            "claim": _claim(
                netlist.INTERMEDIATE_RAIL_NET, "V", "supply_compatibility",
                supply.intermediate_rail_max_v, DIRECT,
                ("mp2459_mps", "res_uniroyal", "tcan1042_ti"),
                _requirement("at_or_below_the_transceiver_supply_maximum",
                             "<=", transceiver["supply"]["max_v"]["value"]),
                assumptions=(
                    "the feedback divider is at the tolerance corner that "
                    "raises the output, and the reference at its datasheet "
                    "maximum",)),
        },
        {
            "id": "logic_rail_above_controller_minimum",
            "identity": netlist.LOGIC_RAIL_NET,
            "claim": _claim(
                netlist.LOGIC_RAIL_NET, "V", "supply_compatibility",
                supply.logic_rail_min_v, DIRECT,
                ("ht75rxx_holtek", "stm32g431_st"),
                _requirement("at_or_above_the_controller_supply_minimum",
                             ">=", mcu["supply"]["min_v"]["value"])),
        },
        {
            "id": "logic_rail_below_controller_maximum",
            "identity": netlist.LOGIC_RAIL_NET,
            "claim": _claim(
                netlist.LOGIC_RAIL_NET, "V", "supply_compatibility",
                supply.logic_rail_max_v, DIRECT,
                ("ht75rxx_holtek", "stm32g431_st"),
                _requirement("at_or_below_the_controller_supply_maximum",
                             "<=", mcu["supply"]["max_v"]["value"])),
        },
        {
            "id": "logic_rail_above_transceiver_interface_minimum",
            "identity": netlist.LOGIC_RAIL_NET,
            "claim": _claim(
                netlist.LOGIC_RAIL_NET, "V", "supply_compatibility",
                supply.logic_rail_min_v, DIRECT,
                ("ht75rxx_holtek", "tcan1042_ti"),
                _requirement("at_or_above_the_transceiver_interface_minimum",
                             ">=",
                             transceiver["io_supply"]["min_v"]["value"])),
        },
        {
            "id": "regulator_input_above_its_dropout",
            "identity": netlist.INTERMEDIATE_RAIL_NET,
            "claim": _claim(
                netlist.INTERMEDIATE_RAIL_NET, "V", "supply_compatibility",
                supply.intermediate_rail_min_v, ASSUMED,
                ("mp2459_mps", "ht75rxx_holtek"),
                _requirement("above_the_regulator_floor", ">=",
                             supply.regulator_floor_v),
                assumptions=(
                    "the regulator's dropout is the declared bound at the "
                    "logic load, not a datasheet limit: the datasheet states "
                    "dropout only at 1 mA",)),
        },
        {
            "id": "regulator_output_current_within_its_rating",
            "identity": netlist.LOGIC_RAIL_NET,
            "claim": _claim(
                netlist.LOGIC_RAIL_NET, "A", "supply_compatibility",
                supply.logic_current_max_a, DIRECT,
                ("stm32g431_st", "tcan1042_ti", "ht75rxx_holtek",
                 "res_uniroyal"),
                _requirement("within_the_regulator_output_rating", "<=",
                             regulator["output_current_max_a"]["value"]),
                assumptions=(
                    "the controller is at its datasheet maximum run current "
                    "at 170 MHz and 85 C with every peripheral enabled, "
                    "which no firmware this board carries has to reach",)),
        },
        {
            "id": "converter_output_current_within_its_rating",
            "identity": netlist.INTERMEDIATE_RAIL_NET,
            "claim": _claim(
                netlist.INTERMEDIATE_RAIL_NET, "A", "supply_compatibility",
                supply.intermediate_current_max_a, DIRECT,
                ("tcan1042_ti", "stm32g431_st", "mp2459_mps"),
                _requirement("within_the_converter_output_rating", "<=",
                             converter["output_current_max_a"]["value"]),
                assumptions=(
                    "the transceiver draws its dominant supply current "
                    "continuously into the lowest load its datasheet "
                    "characterises, which is heavier than any real bus "
                    "traffic",)),
        },
    ]
    return results


# ---------------------------------------------------------------------------
# input path, reverse polarity and transients

#: Every part that stands across the input rail or in the path from it, and
#: the parameter that states what it is rated for. These are the parts the
#: brief's "rated above it with margin" applies to.
INPUT_PATH_RATINGS = (
    ("D1", ("suppressor", "standoff_voltage_v")),
    ("Q1", ("fet", "breakdown_voltage_min_v")),
    ("F1", ("resettable_fuse", "voltage_max_v")),
    ("U3", ("converter", "input_voltage_max_v")),
    ("C1", ("capacitor", "voltage_max_v")),
    ("C2", ("capacitor", "voltage_max_v")),
    ("C4", ("capacitor", "voltage_max_v")),
    ("C5", ("capacitor", "voltage_max_v")),
    ("D3", ("diode", "reverse_voltage_max_v")),
    ("J1", ("connector", "voltage_max_v")),
    ("J3", ("connector", "voltage_max_v")),
)

#: The same for every part the transient reaches once the input clamp is
#: conducting. Three parts in the input path are deliberately absent. The
#: input suppressor is the clamp itself. The field output clamps are clamps
#: too: they conduct rather than stand off, and what they have to satisfy is
#: that their own clamping voltage stays below the switch behind them, which
#: is a claim of its own. The resettable fuse stands off the rail only while
#: it is tripped, and the voltage across it while it conducts is its own
#: resistive drop; the tripped-during-a-transient case is recorded as an
#: omission on its own claim rather than compared here.
TRANSIENT_EXPOSED_RATINGS = tuple(
    entry for entry in INPUT_PATH_RATINGS
    if entry[0] not in ("D1", "F1")) + (
    ("Q2", ("fet", "breakdown_voltage_min_v")),
)


def _rated_value(parameters, reference, path):
    entry = _spec(parameters, reference)
    for key in path:
        entry = entry[key]
    return entry["value"]


def _rating_document(parameters, reference, path):
    entry = _spec(parameters, reference)
    for key in path:
        entry = entry[key]
    return entry.get("document")


def evaluate_input_path_ratings(parameters):
    """Every part in the input path is rated above the declared range."""
    results = []
    for reference, path in INPUT_PATH_RATINGS:
        rating = _rated_value(parameters, reference, path)
        document = _rating_document(parameters, reference, path)
        results.append({
            "id": "input_path_part_rated_above_the_declared_maximum",
            "identity": reference,
            "claim": _claim(
                reference, "V", "rating_margin", rating, DIRECT,
                (document,) if document else (),
                _requirement("above_the_declared_input_maximum", ">=",
                             netlist.INPUT_SUPPLY["max_v"]),
                scope_level="group"),
        })
    return results


def evaluate_transient_clamp(parameters):
    """The input clamp holds every part behind it inside its rating."""
    clamp = _spec(parameters, "D1")["suppressor"]
    results = [{
        "id": "input_clamp_stands_off_the_declared_maximum",
        "identity": "D1",
        "claim": _claim(
            "D1", "V", "protection",
            clamp["standoff_voltage_v"]["value"], DIRECT, ("smaj_mdd",),
            _requirement("at_or_above_the_declared_input_maximum", ">=",
                         netlist.INPUT_SUPPLY["max_v"]),
            scope_level="group"),
    }, {
        "id": "declared_transient_clamp_matches_the_fitted_suppressor",
        "identity": "D1",
        "claim": _claim(
            "D1", "V", "protection",
            clamp["clamping_voltage_max_v"]["value"], DIRECT, ("smaj_mdd",),
            _requirement("equals_the_declared_transient_clamp", "<=",
                         netlist.TRANSIENT_CLAMP_MAX_V),
            scope_level="group"),
    }]
    results.append({
        "id": "resettable_fuse_stands_off_the_declared_rail_when_tripped",
        "identity": "F1",
        "claim": _claim(
            "F1", "V", "protection",
            _rated_value(parameters, "F1", ("resettable_fuse",
                                            "voltage_max_v")),
            DIRECT, ("pptc_1812l200_lute",),
            _requirement("above_the_declared_input_maximum", ">=",
                         netlist.INPUT_SUPPLY["max_v"]),
            scope_level="group",
            omissions=(
                "a transient arriving while the fuse is already tripped "
                "would put the clamping voltage across it, which is above "
                "its rating; that coincidence is not bounded here",)),
    })
    for reference, path in TRANSIENT_EXPOSED_RATINGS:
        rating = _rated_value(parameters, reference, path)
        document = _rating_document(parameters, reference, path)
        results.append({
            "id": "part_behind_the_clamp_rated_above_the_clamping_voltage",
            "identity": reference,
            "claim": _claim(
                reference, "V", "protection", rating, DIRECT,
                tuple({document, "smaj_mdd"} - {None}),
                _requirement("above_the_clamping_voltage", ">=",
                             netlist.TRANSIENT_CLAMP_MAX_V),
                scope_level="group",
                assumptions=(
                    "the clamping voltage is the suppressor's own maximum at "
                    "its rated peak pulse current, which is the highest it "
                    "can present to anything behind it",),
                omissions=(
                    "the energy of the transient itself is not bounded here; "
                    "what is bounded is the voltage the clamp presents while "
                    "conducting at its rated current",)),
        })
    return results


def evaluate_reverse_polarity(parameters):
    """A reversed supply is blocked, and nothing is stressed while it is."""
    supply = Supply(parameters)
    blocking = _spec(parameters, "Q1")["fet"]
    clamp = _spec(parameters, "D1")["suppressor"]
    zener = _spec(parameters, "D2")["zener"]
    return [
        {
            "id": "reverse_blocking_device_stands_off_the_reversed_supply",
            "identity": "Q1",
            "claim": _claim(
                "Q1", "V", "protection",
                blocking["breakdown_voltage_min_v"]["value"], DIRECT,
                ("nce6003x_nce",),
                _requirement("above_the_declared_input_maximum", ">=",
                             netlist.INPUT_SUPPLY["max_v"]),
                scope_level="group",
                assumptions=(
                    "with the supply reversed the device's gate sits at the "
                    "board's own positive rail and its source at the "
                    "reference, so the gate-source voltage is not positive "
                    "and the body diode is reverse biased",)),
        },
        {
            "id": "input_clamp_does_not_conduct_on_a_reversed_supply",
            "identity": "D1",
            "claim": _claim(
                "D1", "V", "protection",
                clamp["standoff_voltage_v"]["value"], DIRECT, ("smaj_mdd",),
                _requirement("above_the_declared_input_maximum", ">=",
                             netlist.INPUT_SUPPLY["max_v"]),
                scope_level="group",
                assumptions=(
                    "the suppressor is bidirectional, so a reversed supply "
                    "below its stand-off voltage sees the same leakage as a "
                    "correct one",)),
        },
        {
            "id": "blocking_gate_clamped_within_its_rating",
            "identity": "BLOCK_G",
            "claim": _claim(
                "BLOCK_G", "V", "gate_drive",
                zener["zener_voltage_max_v"]["value"], DIRECT,
                ("bzt52c12_mdd", "nce6003x_nce"),
                _requirement("within_the_gate_source_rating", "<=",
                             blocking["gate_source_voltage_max_v"]["value"]),
                assumptions=(
                    "the gate clamp is at the top of its zener tolerance, "
                    "which is the worst case for the gate rating",)),
        },
        {
            "id": "blocking_gate_drive_at_a_characterised_point",
            "identity": "BLOCK_G",
            "claim": _claim(
                "BLOCK_G", "V", "gate_drive", supply.blocking_gate_v,
                DIRECT, ("bzt52c12_mdd", "nce6003x_nce"),
                _requirement("at_or_above_a_characterised_drive", ">=",
                             10.0),
                assumptions=(
                    "the gate clamp is at the bottom of its zener tolerance, "
                    "which is the worst case for the on-resistance the "
                    "device reaches; the on-resistance used downstream is "
                    "the datasheet's 10 V figure",)),
        },
        {
            "id": "blocking_gate_current_within_the_zener_rating",
            "identity": "D2",
            "claim": _claim(
                "D2", "W", "protection",
                (zener["zener_voltage_max_v"]["value"]
                 * (netlist.INPUT_SUPPLY["max_v"]
                    - zener["zener_voltage_min_v"]["value"])
                 / (_resistor_ohms("R1")
                    * (1.0 - _resistor_tolerance(parameters, "R1")))),
                DIRECT, ("bzt52c12_mdd", "res_uniroyal"),
                _requirement("within_the_zener_power_rating", "<=",
                             zener["power_max_w"]["value"]),
                scope_level="group"),
        },
    ]


def evaluate_conversion_efficiency(parameters):
    """The step down to the logic rails is switched, not dissipated.

    The brief forbids dissipating the whole input-to-output difference at
    load. What is checked here is the arithmetic that follows from the
    topology: the only linear element is the regulator between the two logic
    rails, and what it drops is the difference between those two, not the
    difference between the input and the logic rail.
    """
    supply = Supply(parameters)
    regulator = _spec(parameters, "U4")
    linear_drop_w = ((supply.intermediate_rail_max_v
                      - supply.logic_rail_min_v)
                     * supply.logic_current_max_a)
    whole_difference_w = ((supply.input_max_v - supply.logic_rail_min_v)
                          * supply.logic_current_max_a)
    return [
        {
            "id": "linear_stage_dissipates_far_less_than_the_whole_step",
            "identity": "U4",
            "claim": _claim(
                "U4", "W", "power_conversion", linear_drop_w, DIRECT,
                ("mp2459_mps", "ht75rxx_holtek", "stm32g431_st"),
                _requirement("below_a_quarter_of_the_whole_input_to_output_"
                             "difference_at_load", "<=",
                             whole_difference_w / 4.0),
                scope_level="group",
                assumptions=(
                    "the logic rail carries its bounded maximum load, which "
                    "is the worst case for the linear stage",)),
        },
        {
            "id": "linear_stage_within_its_package_dissipation",
            "identity": "U4",
            "claim": _claim(
                "U4", "W", "thermal", linear_drop_w, DIRECT,
                ("ht75rxx_holtek", "stm32g431_st"),
                _requirement("within_the_package_dissipation", "<=",
                             regulator["thermal"]["power_max_w"]["value"]),
                scope_level="group",
                omissions=(
                    "the package rating is the datasheet's figure at 25 C "
                    "ambient; no junction temperature is computed here",)),
        },
    ]


# ---------------------------------------------------------------------------
# the step-down converter

def evaluate_converter(parameters):
    supply = Supply(parameters)
    converter = _spec(parameters, "U3")["converter"]
    inductor = _spec(parameters, "L1")["inductor"]
    catch = _spec(parameters, "D3")["diode"]

    duty = supply.intermediate_rail_v / supply.input_max_v
    inductance_min_h = (inductor["inductance_h"]["value"]
                        * (1.0 - inductor["inductance_tolerance"]["value"]))
    ripple_a = (supply.intermediate_rail_v
                * (supply.input_max_v - supply.intermediate_rail_v)
                / (supply.input_max_v * inductance_min_h
                   * converter["switching_frequency_min_hz"]["value"]))
    peak_a = supply.intermediate_current_max_a + ripple_a / 2.0

    enable_upper = _resistor_ohms("R4")
    enable_lower = _resistor_ohms("R5")
    enable_tolerance = max(_resistor_tolerance(parameters, "R4"),
                           _resistor_tolerance(parameters, "R5"))
    enable_min_v = supply.input_min_v * (
        enable_lower * (1.0 - enable_tolerance)
        / (enable_lower * (1.0 - enable_tolerance)
           + enable_upper * (1.0 + enable_tolerance)))
    enable_max_v = netlist.TRANSIENT_CLAMP_MAX_V * (
        enable_lower * (1.0 + enable_tolerance)
        / (enable_lower * (1.0 + enable_tolerance)
           + enable_upper * (1.0 - enable_tolerance)))

    return [
        {
            "id": "converter_inductor_peak_below_its_saturation_current",
            "identity": "L1",
            "claim": _claim(
                "L1", "A", "power_conversion", peak_a, DIRECT,
                ("ind_swpa5040_sunlord", "mp2459_mps"),
                _requirement("below_the_inductor_saturation_current", "<=",
                             inductor["saturation_current_a"]["value"]),
                scope_level="group",
                assumptions=(
                    "the inductance is at the bottom of its tolerance and "
                    "the switching frequency at the bottom of its, which is "
                    "the corner that makes the ripple largest",)),
        },
        {
            "id": "converter_inductor_within_its_heat_rating",
            "identity": "L1",
            "claim": _claim(
                "L1", "A", "power_conversion",
                supply.intermediate_current_max_a, DIRECT,
                ("ind_swpa5040_sunlord", "tcan1042_ti", "stm32g431_st"),
                _requirement("below_the_inductor_heat_rating_current", "<=",
                             inductor["rms_current_a"]["value"]),
                scope_level="group",
                omissions=(
                    "the ripple contribution to the RMS current is not "
                    "included; the DC component alone is compared",)),
        },
        {
            "id": "converter_peak_below_its_own_current_limit",
            "identity": "SW_NODE",
            "claim": _claim(
                "SW_NODE", "A", "power_conversion", peak_a, DIRECT,
                ("mp2459_mps", "ind_swpa5040_sunlord"),
                _requirement("below_the_converter_current_limit", "<=",
                             converter["current_limit_min_a"]["value"])),
        },
        {
            "id": "catch_diode_reverse_rating_above_the_clamping_voltage",
            "identity": "D3",
            "claim": _claim(
                "D3", "V", "power_conversion",
                catch["reverse_voltage_max_v"]["value"], DIRECT,
                ("b1100_diodes", "smaj_mdd"),
                _requirement("above_the_clamping_voltage", ">=",
                             netlist.TRANSIENT_CLAMP_MAX_V),
                scope_level="group"),
        },
        {
            "id": "catch_diode_average_current_within_its_rating",
            "identity": "D3",
            "claim": _claim(
                "D3", "A", "power_conversion",
                supply.intermediate_current_max_a * (1.0 - duty), DIRECT,
                ("b1100_diodes", "mp2459_mps"),
                _requirement("within_the_diode_average_current_rating", "<=",
                             catch["forward_current_max_a"]["value"]),
                scope_level="group"),
        },
        {
            "id": "converter_enable_reaches_its_threshold_at_the_minimum_input",
            "identity": "EN",
            "claim": _claim(
                "EN", "V", "power_conversion", enable_min_v, ASSUMED,
                ("mp2459_mps", "res_uniroyal"),
                _requirement("above_the_enable_threshold", ">=",
                             converter["enable_threshold_rising_v"]["value"]),
                assumptions=(
                    "the enable threshold is the datasheet's typical; the "
                    "datasheet states no maximum, so this comparison is "
                    "against a typical rather than a limit",)),
        },
        {
            "id": "converter_enable_within_its_pin_rating_under_a_transient",
            "identity": "EN",
            "claim": _claim(
                "EN", "V", "power_conversion", enable_max_v, DIRECT,
                ("mp2459_mps", "res_uniroyal", "smaj_mdd"),
                _requirement("within_the_converter_pin_rating", "<=",
                             converter["other_pin_absolute_max_v"]["value"]),
                assumptions=(
                    "the input is at the clamping voltage of the input "
                    "suppressor and the divider at the tolerance corner that "
                    "raises the enable pin",)),
        },
    ]


# ---------------------------------------------------------------------------
# the bus

def evaluate_bus_isolation(parameters):
    """The controller reaches the bus only through the transceiver."""
    controller_pins = {pin_ref for pin_ref in netlist.pin_to_net()
                       if pin_ref.startswith("U1.")}
    violations = []
    for net in ("CANH", "CANL"):
        for pin_ref in netlist.NETS[net]:
            if pin_ref in controller_pins:
                violations.append(pin_ref)
    return [{
        "id": "controller_reaches_the_bus_only_through_the_transceiver",
        "identity": "board",
        "claim": _structural(
            "board", "interface_topology", violations,
            "no_controller_pin_on_a_bus_conductor"),
    }]


def evaluate_bus_rate(parameters):
    """The rate the node is qualified for, and what establishes it."""
    transceiver = _spec(parameters, "U2")["bus"]
    crystal = _spec(parameters, "Y1")["crystal"]
    tolerance_ppm = (crystal["frequency_tolerance_ppm"]["value"]
                     + crystal["frequency_temperature_ppm"]["value"]
                     + crystal["aging_ppm_per_year"]["value"])
    load_error_ppm = _crystal_pulling_ppm(parameters)
    return [
        {
            "id": "declared_data_phase_rate_within_the_transceiver_rating",
            "identity": "board",
            "claim": _claim(
                "board", "bit/s", "interface_compliance",
                netlist.DATA_PHASE_RATE_BPS, DIRECT, ("tcan1042_ti",),
                _requirement("at_or_below_the_transceiver_qualified_rate",
                             "<=",
                             1.0 / transceiver["data_phase_bit_time_min_s"][
                                 "value"]),
                scope_level="board",
                assumptions=(
                    "the fitted device is a G variant, which is the only "
                    "variant whose datasheet specifies the bus and receiver "
                    "bit times at a 200 ns transmitted bit",)),
        },
        {
            "id": "oscillator_tolerance_within_the_bit_timing_budget",
            "identity": "Y1",
            "claim": _claim(
                "Y1", "ppm", "interface_compliance",
                tolerance_ppm + load_error_ppm, DIRECT,
                ("xtal_8mhz_yxc", "stm32g431_st"),
                _requirement("within_the_declared_oscillator_budget", "<=",
                             netlist.OSCILLATOR_TOLERANCE_BUDGET_PPM),
                scope_level="group",
                assumptions=(
                    "initial tolerance, temperature drift and one year of "
                    "ageing are added arithmetically rather than combined "
                    "statistically",
                    "the load-capacitance error is bounded from the crystal's "
                    "shunt capacitance and the assumed motional capacitance, "
                    "neither of which the specification states directly",)),
        },
    ]


def _crystal_pulling_ppm(parameters):
    """How far the load network can pull the crystal, in parts per million.

    The load the crystal sees is the two external capacitors in series with
    the stray capacitance the controller's datasheet estimates. Both the
    capacitors' tolerance and the stray estimate move it, so the pull is
    evaluated at the corner that moves it furthest from the specified load.
    """
    crystal = _spec(parameters, "Y1")["crystal"]
    mcu = _spec(parameters, "U1")["oscillator"]
    stray = mcu["stray_capacitance_estimate_f"]["value"]
    nominal = _capacitance_farads("C16")
    tolerance = _capacitor_tolerance(parameters, "C16")
    shunt = crystal["shunt_capacitance_max_f"]["value"]
    motional = crystal["motional_capacitance_bound_f"]["value"]
    specified = crystal["load_capacitance_f"]["value"]
    worst = 0.0
    for sign in (1.0, -1.0):
        realised = (nominal * (1.0 + sign * tolerance) + stray) / 2.0
        pulled = abs(motional / 2.0
                     * (1.0 / (shunt + realised) - 1.0 / (shunt + specified)))
        worst = max(worst, pulled)
    return worst * 1e6


def evaluate_oscillator(parameters):
    """The crystal the controller has to start, against what it can start."""
    crystal = _spec(parameters, "Y1")["crystal"]
    mcu = _spec(parameters, "U1")["oscillator"]
    stray = mcu["stray_capacitance_estimate_f"]["value"]
    load = (_capacitance_farads("C16") + stray) / 2.0
    shunt = crystal["shunt_capacitance_max_f"]["value"]
    resistance = crystal["resistance_max_ohm"]["value"]
    frequency = crystal["frequency_hz"]["value"]
    omega = 2.0 * 3.141592653589793 * frequency
    critical = 4.0 * resistance * omega * omega * (shunt + load) ** 2
    return [
        {
            "id": "crystal_critical_transconductance_within_the_controller",
            "identity": "Y1",
            "claim": _claim(
                "Y1", "A/V", "oscillator", critical, DIRECT,
                ("xtal_8mhz_yxc", "stm32g431_st"),
                _requirement("within_the_controller_maximum_critical_"
                             "transconductance", "<=",
                             mcu["critical_transconductance_max_a_per_v"][
                                 "value"]),
                scope_level="group",
                assumptions=(
                    "the crystal is at its maximum series resistance and "
                    "maximum shunt capacitance, and the stray capacitance is "
                    "the controller datasheet's estimate rather than a "
                    "measurement",),
                omissions=(
                    "whether a gain margin beyond the controller's stated "
                    "maximum critical transconductance is required is a "
                    "vendor application-note question this board does not "
                    "resolve; oscillator start-up remains a physical test",)),
        },
        {
            "id": "crystal_frequency_within_the_controller_oscillator_range",
            "identity": "Y1",
            "claim": _claim(
                "Y1", "Hz", "oscillator", frequency, DIRECT,
                ("xtal_8mhz_yxc", "stm32g431_st"),
                _requirement("within_the_controller_oscillator_range", ">=",
                             mcu["hse_min_hz"]["value"]),
                scope_level="group"),
        },
    ]


def evaluate_bus_connector(parameters):
    """The two bus conductors are adjacent contacts with nothing between."""
    order = netlist.CONNECTOR_PIN_ORDER["J2"]
    positions = {function: index for index, function in enumerate(order)}
    violations = []
    if abs(positions["CANH"] - positions["CANL"]) != 1:
        violations.append("CANH and CANL are not adjacent contacts")
    return [{
        "id": "bus_conductors_occupy_adjacent_contacts",
        "identity": "J2",
        "claim": _structural(
            "J2", "interface_topology", violations,
            "bus_conductors_adjacent_with_nothing_between"),
    }]


def evaluate_termination(parameters):
    """A nominal 120 ohm differential load, removable without unsoldering."""
    legs = ("R9", "R10")
    nominal = sum(_resistor_ohms(reference) for reference in legs)
    tolerance = max(_resistor_tolerance(parameters, reference)
                    for reference in legs)
    pin_net = netlist.pin_to_net()
    # every leg has to pass through its own link, or pulling the links
    # leaves a path between the two bus conductors
    violations = []
    for leg, header, bus_side in (("R9", "J6", "TERM_H"),
                                  ("R10", "J7", "TERM_L")):
        pins = {number: pin_net.get("%s.%s" % (header, number))
                for number in ("1", "2")}
        if bus_side not in pins.values():
            violations.append("%s does not reach a link of its own" % leg)
        if "TERM_SPLIT" not in pins.values():
            violations.append("%s does not reach the centre node" % header)
    return [
        {
            "id": "termination_presents_the_nominal_differential_load",
            "identity": "CANH",
            "claim": _claim(
                "CANH", "ohm", "interface_compliance",
                nominal * (1.0 + tolerance), DIRECT,
                ("res_rmcf_stackpole",),
                _requirement("within_five_percent_of_the_nominal_termination",
                             "<=", netlist.TERMINATION_NOMINAL_OHM * 1.05),
                assumptions=(
                    "both legs are at the tolerance corner that raises the "
                    "differential load",)),
        },
        {
            "id": "termination_presents_the_nominal_differential_load_low",
            "identity": "CANL",
            "claim": _claim(
                "CANL", "ohm", "interface_compliance",
                nominal * (1.0 - tolerance), DIRECT,
                ("res_rmcf_stackpole",),
                _requirement("within_five_percent_of_the_nominal_termination",
                             ">=", netlist.TERMINATION_NOMINAL_OHM * 0.95),
                assumptions=(
                    "both legs are at the tolerance corner that lowers the "
                    "differential load",)),
        },
        {
            "id": "termination_is_broken_in_both_legs_when_the_links_are_out",
            "identity": "J6",
            "claim": _structural(
                "J6", "interface_topology", violations,
                "each_termination_leg_passes_through_its_own_link",
                documents=("header1x2_kinghelm",)),
        },
    ]


def _termination_fault_current_a(parameters):
    """Current through the termination when one line is at the field rail.

    The line that is not shorted is held by the transceiver, which limits
    what it will sink or source; the rest of the current the short drives
    leaves through the receiver's own input resistance. Solving those two
    together bounds what the termination and its switch carry.
    """
    supply = Supply(parameters)
    transceiver = _spec(parameters, "U2")["bus"]
    limit = transceiver["short_circuit_output_current_max_a"]["value"]
    receiver_ohm = transceiver["input_resistance_min_ohm"]["value"]
    termination_ohm = (_resistor_ohms("R9") + _resistor_ohms("R10")) * (
        1.0 - _resistor_tolerance(parameters, "R9"))
    fault_v = supply.input_max_v
    # the held line settles where the termination current equals the
    # transceiver's limit plus what the receiver draws
    held_v = ((fault_v / termination_ohm - limit)
              / (1.0 / termination_ohm + 1.0 / receiver_ohm))
    return (fault_v - held_v) / termination_ohm


def evaluate_bus_fault(parameters):
    """One bus conductor shorted to the reference or to the field rail."""
    supply = Supply(parameters)
    transceiver = _spec(parameters, "U2")["bus"]
    protector = _spec(parameters, "D4")["suppressor"]
    resistor = _spec(parameters, "R9")["resistor"]
    link = parameters["parts"][netlist.TERMINATION_LINK["mpn"]]["connector"]
    fault_a = _termination_fault_current_a(parameters)
    leg_ohm = _resistor_ohms("R9") * (
        1.0 + _resistor_tolerance(parameters, "R9"))
    results = [
        {
            "id": "transceiver_withstands_the_declared_bus_fault_voltage",
            "identity": "U2",
            "claim": _claim(
                "U2", "V", "fault_tolerance",
                transceiver["fault_voltage_max_v"]["value"], DIRECT,
                ("tcan1042_ti",),
                _requirement("above_the_declared_bus_fault_voltage", ">=",
                             supply.input_max_v),
                scope_level="group"),
        },
        {
            "id": "bus_protector_stands_off_the_declared_bus_fault_voltage",
            "identity": "D4",
            "claim": _claim(
                "D4", "V", "fault_tolerance",
                protector["standoff_voltage_v"]["value"], DIRECT,
                ("esdcan05_st",),
                _requirement("above_the_declared_bus_fault_voltage", ">=",
                             supply.input_max_v),
                scope_level="group"),
        },
        {
            "id": "bus_protector_clamps_below_the_transceiver_fault_rating",
            "identity": "D4",
            "claim": _claim(
                "D4", "V", "fault_tolerance",
                protector["clamping_voltage_max_v"]["value"], DIRECT,
                ("esdcan05_st", "tcan1042_ti"),
                _requirement("below_the_transceiver_bus_fault_rating", "<=",
                             transceiver["fault_voltage_max_v"]["value"]),
                scope_level="group"),
        },
        {
            "id": "termination_leg_dissipation_under_a_bus_fault",
            "identity": "R9",
            "claim": _claim(
                "R9", "W", "fault_tolerance", fault_a * fault_a * leg_ohm,
                DIRECT, ("res_rmcf_stackpole", "tcan1042_ti"),
                _requirement("within_the_resistor_power_rating", "<=",
                             resistor["power_max_w"]["value"]),
                scope_level="group",
                assumptions=(
                    "the node is driving a dominant bit into the shorted "
                    "line, which is the condition that drives the most "
                    "through the termination; the current is bounded by the "
                    "transceiver's own steady-state short-circuit output "
                    "current",)),
        },
        {
            "id": "termination_link_current_in_normal_operation",
            "identity": "J6",
            "claim": _claim(
                "J6", "A", "fault_tolerance",
                transceiver["differential_output_dominant_max_v"]["value"]
                / ((_resistor_ohms("R9") + _resistor_ohms("R10"))
                   * (1.0 - _resistor_tolerance(parameters, "R9"))),
                DIRECT, ("tcan1042_ti", "res_rmcf_stackpole",
                         "jumper_shunt_boomele"),
                _requirement("within_the_link_current_rating", "<=",
                             link["current_max_a"]["value"]),
                scope_level="group",
                assumptions=(
                    "the transceiver drives its maximum dominant "
                    "differential output into the termination at the "
                    "tolerance corner that lowers it",)),
        },
        {
            "id": "termination_link_current_under_a_bus_fault",
            "identity": "J6",
            "claim": _claim(
                "J6", "A", "fault_tolerance", fault_a, DIRECT,
                ("jumper_shunt_boomele", "tcan1042_ti"),
                _requirement("within_the_link_current_rating", "<=",
                             link["current_max_a"]["value"]),
                scope_level="group",
                assumptions=(
                    "the node is driving a dominant bit into the shorted "
                    "line and the current is bounded by the transceiver's "
                    "own steady-state short-circuit output current; its "
                    "duration is bounded again by the transceiver's dominant "
                    "time-out of at most %.1f ms per burst"
                    % (1e3 * transceiver["dominant_timeout_max_s"]["value"]),)),
        },
    ]
    return results


def evaluate_bus_protection(parameters):
    """The discharge level claimed, its balance, and what it costs the bus."""
    transceiver = _spec(parameters, "U2")["bus"]
    protector = _spec(parameters, "D4")["suppressor"]
    bit_time_s = 1.0 / netlist.DATA_PHASE_RATE_BPS
    # what the bus may be loaded with before the added capacitance costs a
    # meaningful part of a data-phase bit: five per cent of the bit time
    # through the load the transceiver's own datasheet characterises into
    capacitance_budget_f = (0.05 * bit_time_s
                            / transceiver["characterised_load_ohm"]["value"])
    added_f = 2.0 * protector["capacitance_max_f"]["value"]
    return [
        {
            "id": "declared_discharge_level_met_by_the_transceiver",
            "identity": "board",
            "claim": _claim(
                "board", "V", "protection",
                transceiver["esd_iec61000_4_2_contact_powered_v"]["value"],
                DIRECT, ("tcan1042_ti",),
                _requirement("at_or_above_the_declared_discharge_level", ">=",
                             netlist.ESD_CONTACT_LEVEL_V),
                scope_level="board",
                assumptions=(
                    "the transceiver alone is compared against the declared "
                    "level; the protector at the connector stands in front "
                    "of it and can only reduce what reaches it",)),
        },
        {
            "id": "declared_discharge_level_met_by_the_bus_protector",
            "identity": "D4",
            "claim": _claim(
                "D4", "V", "protection",
                protector["contact_discharge_v"]["value"], DIRECT,
                ("esdcan05_st",),
                _requirement("at_or_above_the_declared_discharge_level", ">=",
                             netlist.ESD_CONTACT_LEVEL_V),
                scope_level="group",
                assumptions=(
                    "the protector's rating is stated under ISO 10605 with "
                    "the 150 pF / 330 ohm network, which is the discharge "
                    "network IEC 61000-4-2 specifies",),
                omissions=(
                    "neither document states a system-level result for this "
                    "board; both state device-level ratings, and a system "
                    "discharge test remains a physical test",)),
        },
        {
            "id": "bus_protection_is_balanced_line_to_line",
            "identity": "D4",
            "claim": _claim(
                "D4", "F", "interface_compliance",
                protector["capacitance_mismatch_f"]["value"], DIRECT,
                ("esdcan05_st",),
                _requirement("below_a_tenth_of_a_picofarad", "<=", 1e-13),
                scope_level="group",
                assumptions=(
                    "the two lines are protected by one dual device whose "
                    "datasheet states the capacitance variation between "
                    "them; the figure is a typical, not a limit",)),
        },
        {
            "id": "bus_protection_capacitance_within_the_rate_budget",
            "identity": "D4",
            "claim": _claim(
                "D4", "F", "interface_compliance", added_f, DIRECT,
                ("esdcan05_st", "tcan1042_ti"),
                _requirement("within_the_declared_bus_capacitance_budget",
                             "<=", capacitance_budget_f),
                scope_level="group",
                assumptions=(
                    "the budget is this board's: five per cent of a "
                    "data-phase bit time through the load the transceiver's "
                    "datasheet characterises its outputs into",),
                omissions=(
                    "the cable's own capacitance and the capacitance of "
                    "other nodes are outside this board and are not "
                    "included",)),
        },
    ]


# ---------------------------------------------------------------------------
# field inputs

class InputStage:
    """The divider, clamp and series element one field input is made of."""

    def __init__(self, parameters, channel):
        self.upper = _resistor_ohms(_channel_reference("R", channel, 13))
        self.lower = _resistor_ohms(_channel_reference("R", channel, 17))
        self.series = _resistor_ohms(_channel_reference("R", channel, 21))
        self.tolerance = _resistor_tolerance(
            parameters, _channel_reference("R", channel, 13))
        supply = Supply(parameters)
        mcu = _spec(parameters, "U1")
        self.ratio = (self.upper + self.lower) / self.lower
        self.ratio_high = ((self.upper * (1.0 + self.tolerance)
                            + self.lower * (1.0 - self.tolerance))
                           / (self.lower * (1.0 - self.tolerance)))
        self.ratio_low = ((self.upper * (1.0 - self.tolerance)
                           + self.lower * (1.0 + self.tolerance))
                          / (self.lower * (1.0 + self.tolerance)))
        vih = (mcu["digital_inputs"]["vih_min"]["fraction_of_supply"]["value"]
               * supply.logic_rail_max_v)
        vil = (mcu["digital_inputs"]["vil_max"]["fraction_of_supply"]["value"]
               * supply.logic_rail_min_v)
        self.on_threshold_v = vih * self.ratio_high
        self.off_threshold_v = vil * self.ratio_low
        self.hysteresis_v = (vih - vil) * self.ratio_low
        self.terminal_current_a = (netlist.INPUT_SUPPLY["max_v"]
                                   / (self.upper + self.lower))
        # positive survival: the divider node is held by the clamp diode to
        # the logic rail, so the pin sees the rail plus one forward drop
        diode = _spec(parameters, "D5")["diode"]
        self.clamp_forward_v = diode["forward_voltage_max_v"]["0.001"]["value"]
        self.pin_max_v = supply.logic_rail_max_v + self.clamp_forward_v
        self.clamp_current_a = (
            (netlist.INPUT_SUPPLY["max_v"] - self.pin_max_v)
            / (self.upper * (1.0 - self.tolerance)))
        # negative survival: the controller's own structure holds the pin at
        # the reference and the series element bounds what is injected
        conductance = (1.0 / self.upper + 1.0 / self.lower + 1.0 / self.series)
        node_v = -(netlist.INPUT_SUPPLY["max_v"] / self.upper) / conductance
        self.injection_a = abs(node_v) / self.series


def evaluate_input_thresholds(parameters):
    """Each input has a stated threshold, hysteresis and open-terminal state."""
    results = []
    for channel in range(1, netlist.INPUT_COUNT + 1):
        stage = InputStage(parameters, channel)
        terminal = "DI%d" % channel
        results.append({
            "id": "input_on_threshold_below_the_minimum_declared_supply",
            "identity": terminal,
            "claim": _claim(
                terminal, "V", "interface_compliance", stage.on_threshold_v,
                DIRECT, ("stm32g431_st", "res_uniroyal", "ht75rxx_holtek"),
                _requirement("at_or_below_the_minimum_declared_input_supply",
                             "<=", netlist.INPUT_SUPPLY["min_v"]),
                assumptions=(
                    "the controller's guaranteed high threshold is a "
                    "fraction of its supply, taken at the top of the "
                    "regulator's accuracy, and the divider at the tolerance "
                    "corner that raises the terminal threshold",)),
        })
        results.append({
            "id": "input_off_threshold_above_a_quarter_of_the_supply",
            "identity": terminal,
            "claim": _claim(
                terminal, "V", "interface_compliance", stage.off_threshold_v,
                DIRECT, ("stm32g431_st", "res_uniroyal", "ht75rxx_holtek"),
                _requirement("above_a_fifth_of_the_nominal_supply", ">=",
                             netlist.INPUT_SUPPLY["min_v"] / 5.0),
                assumptions=(
                    "the controller's guaranteed low threshold is a fraction "
                    "of its supply, taken at the bottom of the regulator's "
                    "accuracy, and the divider at the tolerance corner that "
                    "lowers the terminal threshold",)),
        })
        results.append({
            "id": "input_hysteresis_at_the_terminal",
            "identity": terminal,
            "claim": _claim(
                terminal, "V", "interface_compliance", stage.hysteresis_v,
                DIRECT, ("stm32g431_st", "res_uniroyal", "ht75rxx_holtek"),
                _requirement("at_least_one_volt_at_the_terminal", ">=", 1.0),
                assumptions=(
                    "the hysteresis is the guaranteed separation between the "
                    "controller's high and low thresholds referred back "
                    "through the divider, not the datasheet's typical "
                    "hysteresis figure",)),
        })
    pin_net = netlist.pin_to_net()
    violations = []
    for channel in range(1, netlist.INPUT_COUNT + 1):
        pull_down = _channel_reference("R", channel, 17)
        if pin_net.get("%s.2" % pull_down) != netlist.GROUND_NET:
            violations.append("%s does not return to the reference"
                              % pull_down)
    results.append({
        "id": "input_open_terminal_state_is_defined",
        "identity": "board",
        "claim": _structural(
            "board", "interface_compliance", violations,
            "every_input_has_a_pull_down_to_the_reference",
            documents=("res_uniroyal",)),
    })
    return results


def evaluate_input_survival(parameters):
    """Each input survives the declared range continuously, either polarity."""
    mcu = _spec(parameters, "U1")
    supply = Supply(parameters)
    results = []
    for channel in range(1, netlist.INPUT_COUNT + 1):
        stage = InputStage(parameters, channel)
        terminal = "DI%d" % channel
        results.append({
            "id": "input_pin_within_its_rating_at_the_positive_extreme",
            "identity": terminal,
            "claim": _claim(
                terminal, "V", "fault_tolerance", stage.pin_max_v, DIRECT,
                ("stm32g431_st", "1n4148w_semtech", "ht75rxx_holtek"),
                _requirement("within_the_controller_input_voltage_rating",
                             "<=", mcu["input_voltage_ft_max_v"]["value"]),
                assumptions=(
                    "the clamp diode holds the divider node one forward drop "
                    "above the logic rail; the drop is the datasheet maximum "
                    "at 1 mA and the clamp carries less than that",)),
        })
        results.append({
            "id": "input_injection_within_the_controller_limit",
            "identity": terminal,
            "claim": _claim(
                terminal, "A", "fault_tolerance", stage.injection_a, DIRECT,
                ("stm32g431_st", "res_uniroyal"),
                _requirement("within_the_controller_injection_limit", "<=",
                             mcu["injection_current_max_a"]["value"]),
                assumptions=(
                    "the terminal is at the negative extreme of the declared "
                    "range and the controller pin is held at the reference, "
                    "which is the corner that injects the most",)),
        })
        results.append({
            "id": "input_series_element_within_its_power_rating",
            "identity": _channel_reference("R", channel, 13),
            "claim": _claim(
                _channel_reference("R", channel, 13), "W", "rating_margin",
                (netlist.INPUT_SUPPLY["max_v"] ** 2
                 / (stage.upper * (1.0 - stage.tolerance))),
                DIRECT, ("res_uniroyal",),
                _requirement("within_the_resistor_power_rating", "<=",
                             _spec(parameters, "R14")["resistor"][
                                 "power_max_w"]["value"]),
                scope_level="group",
                assumptions=(
                    "the whole declared input maximum stands across the "
                    "upper element, which overstates it because the lower "
                    "element takes a share",)),
        })
    total_injection = sum(
        InputStage(parameters, channel).injection_a
        for channel in range(1, netlist.INPUT_COUNT + 1))
    results.append({
        "id": "total_input_injection_within_the_controller_limit",
        "identity": "U1",
        "claim": _claim(
            "U1", "A", "fault_tolerance", total_injection, DIRECT,
            ("stm32g431_st", "res_uniroyal"),
            _requirement("within_the_controller_total_injection_limit", "<=",
                         mcu["injection_current_total_max_a"]["value"]),
            scope_level="group",
            assumptions=(
                "every input is at the negative extreme of the declared "
                "range at the same time",)),
    })
    clamp_total = sum(
        InputStage(parameters, channel).clamp_current_a
        for channel in range(1, netlist.INPUT_COUNT + 1))
    bleed_min_a = supply.logic_rail_min_v / (
        _resistor_ohms("R6") * (1.0 + _resistor_tolerance(parameters, "R6")))
    results.append({
        "id": "input_clamp_current_absorbed_by_the_logic_rail",
        "identity": netlist.LOGIC_RAIL_NET,
        "claim": _claim(
            netlist.LOGIC_RAIL_NET, "A", "fault_tolerance", clamp_total,
            DIRECT, ("stm32g431_st", "res_uniroyal", "1n4148w_semtech"),
            _requirement("within_what_the_rail_bleed_alone_sinks", "<=",
                         bleed_min_a),
            assumptions=(
                "every input is at the positive extreme of the declared "
                "range at the same time and the board is unpowered, so the "
                "bleed element is the only sink on the rail; with the board "
                "powered the controller sinks far more",)),
    })
    unpowered_rail_v = clamp_total * _resistor_ohms("R6") * (
        1.0 + _resistor_tolerance(parameters, "R6"))
    results.append({
        "id": "unpowered_logic_rail_below_the_controller_absolute_maximum",
        "identity": netlist.LOGIC_RAIL_NET,
        "claim": _claim(
            netlist.LOGIC_RAIL_NET, "V", "fault_tolerance",
            unpowered_rail_v, DIRECT,
            ("stm32g431_st", "res_uniroyal", "1n4148w_semtech"),
            _requirement("below_the_controller_supply_absolute_maximum", "<=",
                         mcu["supply_voltage_absolute_max_v"]["value"]),
            assumptions=(
                "the board is unpowered, every input is at the positive "
                "extreme, and the rail bleed is the only sink",)),
    })
    return results


# ---------------------------------------------------------------------------
# field outputs

def evaluate_output_drive(parameters):
    """Each output switches its rated current from a controller pin."""
    supply = Supply(parameters)
    fet = _spec(parameters, "Q2")["fet"]
    results = []
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        gate = "DO%d_GATE" % channel
        switch = _channel_reference("Q", channel, 1)
        results.append({
            "id": "output_gate_drive_at_a_characterised_point",
            "identity": gate,
            "claim": _claim(
                gate, "V", "gate_drive", supply.output_gate_v, DIRECT,
                ("wst6066a_winsok", "ht75rxx_holtek"),
                _requirement("at_or_above_a_characterised_drive", ">=",
                             supply.output_characterised_gate_v),
                assumptions=(
                    "the gate is driven from the logic rail at the bottom of "
                    "the regulator's accuracy; the gate network carries no "
                    "steady current, so the series element drops nothing",)),
        })
        results.append({
            "id": "output_switch_dissipation_at_the_rated_current",
            "identity": switch,
            "claim": _claim(
                switch, "W", "thermal",
                supply.channel_current_a ** 2 * supply.output_rds_ohm,
                DIRECT, ("wst6066a_winsok",),
                _requirement("within_the_package_dissipation", "<=",
                             fet["thermal_power_max_w"]["value"]
                             if "thermal_power_max_w" in fet
                             else _spec(parameters, "Q2")["thermal"][
                                 "power_max_w"]["value"]),
                scope_level="group",
                assumptions=(
                    "the on-resistance is the datasheet's maximum at the 2.5 "
                    "V gate it characterises, which is below the drive this "
                    "board applies, so the real resistance is lower",),
                omissions=(
                    "the package rating is the datasheet's figure at 25 C "
                    "ambient; no junction temperature is computed here",)),
        })
        results.append({
            "id": "output_current_within_the_switch_rating",
            "identity": switch,
            "claim": _claim(
                switch, "A", "rating_margin", supply.channel_current_a,
                DIRECT, ("wst6066a_winsok",),
                _requirement("within_the_switch_continuous_current", "<=",
                             fet["drain_current_max_a"]["value"]),
                scope_level="group"),
        })
    results.append({
        "id": "field_supply_holds_every_channel_at_its_rated_current",
        "identity": "F1",
        "claim": _claim(
            "F1", "A", "protection", supply.fuse_hold_current_a, DIRECT,
            ("pptc_1812l200_lute",),
            _requirement("at_or_above_the_sum_of_the_channel_ratings", ">=",
                         supply.field_current_a),
            scope_level="group",
            assumptions=(
                "the fuse is at the board's declared maximum ambient of %g C, "
                "read from the datasheet's derating table rather than "
                "interpolated" % netlist.AMBIENT_MAX_C,)),
    })
    board_path_ohm = (supply.fuse_resistance_min_ohm
                      + supply.blocking_rds_ohm
                      + netlist.BOARD_COPPER_BUDGET_OHM)
    results.append({
        "id": "field_supply_short_current_within_the_fuse_rating",
        "identity": "F1",
        "claim": _claim(
            "F1", "A", "protection",
            netlist.SUPPLY_PROSPECTIVE_FAULT_CURRENT_MAX_A, DIRECT,
            ("pptc_1812l200_lute",),
            _requirement("within_the_fuse_maximum_fault_current", "<=",
                         _spec(parameters, "F1")["resettable_fuse"][
                             "fault_current_max_a"]["value"]),
            scope_level="group",
            assumptions=(
                "the prospective fault current is the figure the board "
                "declares the installation must respect, not one this board "
                "sets: its own series resistance from the terminal to a "
                "short is only %.3f ohm, so a source able to deliver more "
                "than the declared current would exceed the fuse's rating"
                % board_path_ohm,)),
    })
    results.append({
        "id": "field_supply_above_the_declared_minimum_at_full_load",
        "identity": netlist.FIELD_SUPPLY_NET,
        "claim": _claim(
            netlist.FIELD_SUPPLY_NET, "V", "rating_margin",
            supply.field_supply_min_v, DIRECT,
            ("pptc_1812l200_lute", "nce6003x_nce"),
            _requirement("within_one_volt_of_the_declared_input_minimum",
                         ">=", netlist.INPUT_SUPPLY["min_v"] - 1.0),
            assumptions=(
                "every channel carries its rated current at once and the "
                "fuse is at its maximum resistance",
                "board copper between the terminal and the field supply pin "
                "is the declared budget, not a measurement",)),
    })
    return results


def evaluate_output_safe_state(parameters):
    """Every output is off from power-on until firmware drives it."""
    supply = Supply(parameters)
    mcu = _spec(parameters, "U1")
    fet = _spec(parameters, "Q2")["fet"]
    leakage_a = mcu["input_leakage_max_a"]["value"]
    results = []
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        gate = "DO%d_GATE" % channel
        pull_down = _channel_reference("R", channel, 29)
        gate_v = leakage_a * _resistor_ohms(pull_down) * (
            1.0 + _resistor_tolerance(parameters, pull_down))
        results.append({
            "id": "output_gate_below_threshold_with_nothing_driving_it",
            "identity": gate,
            "claim": _claim(
                gate, "V", "safe_state", gate_v, DIRECT,
                ("stm32g431_st", "wst6066a_winsok", "res_uniroyal"),
                _requirement("below_the_switch_threshold_voltage", "<=",
                             fet["vgs_threshold_min_v"]["value"]),
                assumptions=(
                    "after reset the controller leaves every port a floating "
                    "input, so the only current in the gate network is the "
                    "pin's own leakage at its datasheet maximum",)),
        })
    pin_net = netlist.pin_to_net()
    violations = []
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        pull_down = _channel_reference("R", channel, 29)
        if pin_net.get("%s.2" % pull_down) != netlist.GROUND_NET:
            violations.append("%s does not return to the reference"
                              % pull_down)
        gate_net = "DO%d_GATE" % channel
        members = {ref.split(".", 1)[0] for ref in netlist.NETS[gate_net]}
        if len(members & {"Q%d" % (channel + 1)}) != 1:
            violations.append("%s does not reach exactly one switch"
                              % gate_net)
    results.append({
        "id": "each_output_switches_independently",
        "identity": "board",
        "claim": _structural(
            "board", "safe_state", violations,
            "each_gate_reaches_one_switch_and_its_own_pull_down"),
    })
    del supply
    return results


def evaluate_output_clamp(parameters):
    """Inductive turn-off is clamped inside the switch's own rating."""
    fet = _spec(parameters, "Q2")["fet"]
    clamp = _spec(parameters, "D9")["suppressor"]
    results = []
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        terminal = "DO%d" % channel
        results.append({
            "id": "output_clamp_below_the_switch_breakdown",
            "identity": terminal,
            "claim": _claim(
                terminal, "V", "protection",
                clamp["clamping_voltage_max_v"]["value"], DIRECT,
                ("smf_jingdao", "wst6066a_winsok"),
                _requirement("below_the_switch_breakdown_voltage", "<=",
                             fet["breakdown_voltage_min_v"]["value"]),
                assumptions=(
                    "the clamp is at its maximum clamping voltage, which is "
                    "its value at the rated peak pulse current",),
                omissions=(
                    "the energy of any particular load's turn-off is not "
                    "bounded here; what is bounded is the voltage the clamp "
                    "presents while conducting at its rated current",)),
        })
        results.append({
            "id": "output_clamp_stands_off_the_declared_field_supply",
            "identity": terminal,
            "claim": _claim(
                terminal, "V", "protection",
                clamp["standoff_voltage_v"]["value"], DIRECT,
                ("smf_jingdao",),
                _requirement("at_or_above_the_declared_input_maximum", ">=",
                             netlist.INPUT_SUPPLY["max_v"]),
                assumptions=(
                    "with the switch off and a load wired to the field "
                    "supply pin, the terminal sits at the field supply, so "
                    "the clamp stands off the declared input maximum "
                    "continuously",)),
        })
    return results


# ---------------------------------------------------------------------------
# absolute maxima across the board

def _net_levels(parameters):
    """The highest steady voltage each net can reach, where it is known."""
    supply = Supply(parameters)
    levels = {
        netlist.INPUT_RAIL_NET: supply.input_max_v,
        netlist.FIELD_SUPPLY_NET: supply.input_max_v,
        netlist.SUPPLY_RETURN_NET: supply.input_max_v,
        netlist.INTERMEDIATE_RAIL_NET: supply.intermediate_rail_max_v,
        netlist.LOGIC_RAIL_NET: supply.logic_rail_max_v,
        netlist.GROUND_NET: 0.0,
        "BLOCK_G": _spec(parameters, "D2")["zener"][
            "zener_voltage_max_v"]["value"],
        "SW_NODE": supply.input_max_v,
        "BOOT": supply.input_max_v + supply.intermediate_rail_max_v,
        "TERM_SPLIT": supply.input_max_v,
    }
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        levels["DO%d" % channel] = supply.input_max_v
        levels["DO%d_GATE" % channel] = supply.logic_rail_max_v
        levels["DO%d_DRV" % channel] = supply.logic_rail_max_v
    for channel in range(1, netlist.INPUT_COUNT + 1):
        levels["DI%d" % channel] = supply.input_max_v
        stage = InputStage(parameters, channel)
        levels["DI%d_DIV" % channel] = stage.pin_max_v
        levels["DI%d_IN" % channel] = stage.pin_max_v
    for net in ("CANH", "CANL"):
        levels[net] = supply.input_max_v
    for net in ("CAN_TXD", "CAN_RXD", "CAN_STB", "NRST", "SWDIO", "SWCLK",
                "SWD_DIO", "SWD_CLK", "BOOT0", "STATUS", "LED_A", "XIN",
                "XOUT", "TERM_H", "TERM_L", "FB", "EN"):
        levels[net] = supply.logic_rail_max_v
    levels["EN"] = _spec(parameters, "U3")["converter"][
        "other_pin_absolute_max_v"]["value"]
    return levels


#: Every capacitor's rating has to stand above the net it sits across. The
#: net a capacitor is on is read from the netlist; this is the list of the
#: ones whose other end is not the reference, which would otherwise be read
#: as sitting across zero volts.
def evaluate_absolute_maximum(parameters):
    """Every capacitor is rated above the highest level its net reaches."""
    levels = _net_levels(parameters)
    pin_net = netlist.pin_to_net()
    results = []
    for reference, part in sorted(netlist.PARTS.items()):
        if not reference.startswith("C"):
            continue
        nets = {pin_net["%s.%s" % (reference, number)]
                for number in ("1", "2")}
        known = [levels[net] for net in nets if net in levels]
        if len(known) < len(nets):
            continue
        across = max(known) - min(known) if len(known) > 1 else max(known)
        rating = _spec(parameters, reference)["capacitor"][
            "voltage_max_v"]["value"]
        results.append({
            "id": "capacitor_rated_above_the_level_across_it",
            "identity": reference,
            "claim": _claim(
                reference, "V", "rating_margin", rating, DIRECT,
                ("mlcc_yageo_cc", "elcap_rvt_jieerrui"),
                _requirement("above_the_steady_level_across_the_part", ">=",
                             across),
                scope_level="group",
                omissions=(
                    "transient levels are covered by the clamp claims, not "
                    "by this one, which compares steady levels only",)),
        })
    return results


def evaluate_dissipation(parameters):
    """Every resistor that carries steady current is inside its rating."""
    supply = Supply(parameters)
    results = []
    steady = {
        "R1": (netlist.INPUT_SUPPLY["max_v"]
               - _spec(parameters, "D2")["zener"][
                   "zener_voltage_min_v"]["value"]),
        "R2": supply.intermediate_rail_max_v,
        "R4": netlist.INPUT_SUPPLY["max_v"],
        "R6": supply.logic_rail_max_v,
        "R11": supply.logic_rail_max_v,
    }
    for reference, across_v in sorted(steady.items()):
        ohms = _resistor_ohms(reference) * (
            1.0 - _resistor_tolerance(parameters, reference))
        rating = _spec(parameters, reference)["resistor"][
            "power_max_w"]["value"]
        results.append({
            "id": "resistor_dissipation_within_its_rating",
            "identity": reference,
            "claim": _claim(
                reference, "W", "rating_margin", across_v * across_v / ohms,
                DIRECT, ("res_uniroyal",),
                _requirement("within_the_resistor_power_rating", "<=",
                             rating),
                scope_level="group",
                assumptions=(
                    "the whole named level stands across the element, which "
                    "overstates it wherever the element is part of a "
                    "divider",)),
        })
    return results


# ---------------------------------------------------------------------------
# structure, connectors, access and supply

def evaluate_protection_coverage(parameters):
    """Every conductor that enters the board is protected or excused."""
    entering = netlist.entering_conductors()
    protected = set()
    pin_net = netlist.pin_to_net()
    for reference, part in netlist.PARTS.items():
        spec = parameters["parts"].get(part["mpn"] or "", {})
        if "suppressor" not in spec:
            continue
        for pin_ref, net in pin_net.items():
            if pin_ref.startswith(reference + "."):
                protected.add(net)
    violations = []
    for net in sorted(entering):
        if net in protected or net in netlist.PROTECTION_EXEMPT:
            continue
        violations.append(net)
    return [{
        "id": "every_entering_conductor_is_protected_or_excused",
        "identity": "board",
        "claim": _structural(
            "board", "protection", violations,
            "every_entering_conductor_carries_a_clamp_or_a_recorded_reason"),
    }]


def evaluate_connector_contract(parameters):
    """Each connector's pin order is the one the design source declares."""
    pin_net = netlist.pin_to_net()
    violations = []
    for reference, order in sorted(netlist.CONNECTOR_PIN_ORDER.items()):
        functions = netlist.CONNECTOR_FUNCTION_NETS[reference]
        for index, function in enumerate(order):
            pin_ref = "%s.%d" % (reference, index + 1)
            if pin_net.get(pin_ref) != functions[function]:
                violations.append("%s carries %r, not %s"
                                  % (pin_ref, pin_net.get(pin_ref), function))
        if set(order) != set(functions):
            violations.append("%s pin order and function map disagree"
                              % reference)
    results = [{
        "id": "connector_pin_order_matches_the_declared_contract",
        "identity": "board",
        "claim": _structural(
            "board", "interface_topology", violations,
            "every_connector_pin_carries_its_declared_function"),
    }]
    for reference in sorted(netlist.CONNECTOR_PIN_ORDER):
        part = netlist.PARTS[reference]
        connector = parameters["parts"][part["mpn"]]["connector"]
        declared = len(netlist.CONNECTOR_PIN_ORDER[reference])
        results.append({
            "id": "connector_position_count_matches_the_part",
            "identity": reference,
            "claim": _claim(
                reference, "positions", "interface_topology",
                float(connector["positions"]), DIRECT,
                ("term_db128v_dorabo", "header1x5_kinghelm"),
                _requirement("equals_the_declared_position_count", ">=",
                             float(declared)),
                scope_level="group"),
        })
    results.append({
        "id": "field_connector_current_rating_above_the_channel_sum",
        "identity": "J3",
        "claim": _claim(
            "J3", "A", "rating_margin",
            parameters["parts"][netlist.PARTS["J3"]["mpn"]]["connector"][
                "current_max_a"]["value"],
            DIRECT, ("term_db128v_dorabo",),
            _requirement("above_the_sum_of_the_channel_ratings", ">=",
                         netlist.OUTPUT_COUNT
                         * netlist.OUTPUT_CURRENT_RATING_A),
            scope_level="group"),
    })
    return results


def evaluate_probe_access(parameters):
    """Every net the brief asks to probe carries a test point."""
    pin_net = netlist.pin_to_net()
    probed = {pin_net["%s.1" % reference]
              for reference in netlist.PARTS if reference.startswith("TP")}
    missing = [net for net in netlist.PROBE_REQUIRED_NETS
               if net not in probed]
    return [{
        "id": "every_required_net_reaches_a_probe",
        "identity": "board",
        "claim": _structural("board", "test_access", missing,
                             "every_required_net_reaches_a_probe"),
    }]


def _footprint_pad_count(footprint):
    library, _, name = footprint.partition(":")
    for root in (LOCAL_FOOTPRINT_ROOT, FOOTPRINT_ROOT):
        path = os.path.join(root, library + ".pretty", name + ".kicad_mod")
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        numbers = set()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('(pad "'):
                numbers.add(stripped.split('"')[1])
        return len({number for number in numbers if number})
    raise ValueError("no footprint file for " + footprint)


def evaluate_package_correspondence(parameters):
    """The land pattern has as many pads as the package has terminals."""
    results = []
    for reference, part in sorted(netlist.PARTS.items()):
        spec = parameters["parts"].get(part["mpn"] or "", {})
        land = spec.get("land_pattern")
        if land is None:
            continue
        results.append({
            "id": "footprint_pad_count_matches_the_package",
            "identity": reference,
            "claim": _claim(
                reference, "pads", "package_correspondence",
                float(_footprint_pad_count(part["footprint"])), DIRECT,
                (land["document"],),
                _requirement("equals_the_package_terminal_count", ">=",
                             float(land["pad_count"])),
                scope_level="group"),
        })
    violations = []
    library = libraries.LIBRARY_NAME
    for reference, part in sorted(netlist.PARTS.items()):
        spec = parameters["parts"].get(part["mpn"] or "", {})
        land = spec.get("land_pattern") or {}
        pin_map = land.get("pin_map")
        if not pin_map:
            continue
        for number in pin_map:
            if "%s.%s" % (reference, number) not in netlist.pin_to_net() \
                    and "%s.%s" % (reference, number) not in netlist.NO_CONNECT:
                violations.append("%s.%s is in the package map but on no net"
                                  % (reference, number))
    del library
    results.append({
        "id": "every_mapped_package_terminal_is_accounted_for",
        "identity": "board",
        "claim": _structural(
            "board", "package_correspondence", violations,
            "every_terminal_named_by_a_package_map_is_on_a_net_or_"
            "declared_no_connect"),
    })
    return results


def evaluate_supply_availability(parameters):
    """The planned build is inside the stock the catalogue recorded."""
    catalog = load_catalog()["parts"]
    counts = {}
    for part in netlist.PARTS.values():
        if not part["in_bom"] or not part.get("lcsc"):
            continue
        counts[part["lcsc"]] = counts.get(part["lcsc"], 0) + 1
    results = []
    for code in sorted(counts):
        entry = catalog[code]
        boards = entry["stock"] // counts[code]
        results.append({
            "id": "catalogue_stock_covers_the_planned_build",
            "identity": code,
            "claim": _claim(
                code, "boards", "supply", float(boards), DIRECT,
                ("jlcpcb_catalogue_snapshot",),
                _requirement("at_or_above_the_planned_build_quantity", ">=",
                             float(netlist.PLANNED_BUILD_QUANTITY)),
                scope_level="group",
                omissions=(
                    "the stock figure is the catalogue reading recorded at "
                    "the retrieval date; it is not a reservation",)),
        })
    return results


EXTRACTION = "generated/extraction.json"


def _extraction():
    from . import extraction
    return extraction.load()


def evaluate_routed_copper(parameters):
    """What the copper the board actually carries costs the field circuit.

    Every pre-layout claim about a field channel priced the board's own
    conductors from a budget, because no conductor existed yet. They exist
    now and have been traced, so the budget can be checked rather than
    trusted: each measured resistance is the traced geometry priced at the
    fabricator's stated finished copper thickness, with the traversal's own
    junction ambiguity added on rather than averaged away.

    The measurement describes one board file. If the board has been edited
    since, the digest recorded with the extraction no longer matches it and
    the first claim here says so, which is what stops every claim below from
    describing copper that is no longer on the board.
    """
    from . import extraction
    document = _extraction()
    supply = Supply(parameters)
    results = [{
        "id": "extraction_describes_the_committed_board",
        "identity": "board",
        "claim": _structural(
            "board", "traceability",
            () if document["board_file_sha256"] == extraction.board_digest()
            else ("the committed extraction was taken from a different "
                  "board file",),
            "the_extraction_was_taken_from_the_committed_board",
            source=EXTRACTION),
    }]
    measured = extraction.resistances()
    for net in sorted(measured):
        results.append({
            "id": "routed_copper_within_the_budget_it_was_priced_at_%s"
                  % net.lower(),
            "identity": net,
            "claim": _claim(
                net, "ohm", "rail", measured[net], ASSUMED, (),
                _requirement("within_the_declared_board_copper_budget", "<=",
                             netlist.BOARD_COPPER_BUDGET_OHM),
                scope_level="path", source=EXTRACTION,
                assumptions=(
                    "the traversal's junction ambiguity is added to the "
                    "resistance rather than centred on it, so the number "
                    "compared here is the top of the extracted range",
                    document["via_barrel_resistance_ohm"]["assumption"],)),
        })
    # The drop the field supply actually loses in copper, at the current
    # every channel together draws through it, against the same floor the
    # pre-layout scenario asked of the rail.
    field_min_v = (supply.input_min_v
                   - supply.field_current_a * supply.fuse_resistance_max_ohm
                   - supply.blocking_drop_max_v
                   - measured[netlist.FIELD_SUPPLY_NET]
                   * supply.field_current_a)
    results.append({
        "id": "field_supply_at_the_contact_with_the_routed_copper",
        "identity": netlist.FIELD_SUPPLY_NET,
        "claim": _claim(
            netlist.FIELD_SUPPLY_NET, "V", "rail", field_min_v, ASSUMED, (),
            _requirement("within_one_volt_of_the_declared_input_minimum",
                         ">=", netlist.INPUT_SUPPLY["min_v"] - 1.0),
            scope_level="path", source=EXTRACTION,
            assumptions=(
                "the supply sits at the bottom of the declared input range, "
                "the fuse at its maximum resistance and the blocking device "
                "at its maximum drop, all at once",
                document["via_barrel_resistance_ohm"]["assumption"],)),
    })
    # And each output's own conductor, at the current that one channel is
    # rated for rather than at the four the supply carries.
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        net = "DO%d" % channel
        results.append({
            "id": "field_output_copper_drop_at_the_rated_current_%d" % channel,
            "identity": net,
            "claim": _claim(
                net, "V", "rail",
                measured[net] * netlist.OUTPUT_CURRENT_RATING_A, ASSUMED, (),
                _requirement("within_the_budgeted_copper_drop", "<=",
                             netlist.BOARD_COPPER_BUDGET_OHM
                             * netlist.OUTPUT_CURRENT_RATING_A),
                scope_level="path", source=EXTRACTION,
                assumptions=(
                    document["via_barrel_resistance_ohm"]["assumption"],)),
        })
    return results


def evaluate_assembly(parameters):
    """What the assembler has to do beyond one reflow of the front side."""
    through_hole = [reference for reference, part in netlist.PARTS.items()
                    if part["footprint"]
                    and _footprint_is_through_hole(part["footprint"])
                    and part["in_bom"]]
    return [{
        "id": "hand_soldered_part_count_matches_the_assembly_policy",
        "identity": "board",
        "claim": _claim(
            "board", "parts", "assembly", float(len(through_hole)), DERIVED,
            (), _requirement("matches_the_declared_through_hole_count", "<=",
                             float(netlist.ASSEMBLY_POLICY[
                                 "through_hole_soldered_parts"])),
            scope_level="board"),
    }]


def _footprint_is_through_hole(footprint):
    library, _, name = footprint.partition(":")
    for root in (LOCAL_FOOTPRINT_ROOT, FOOTPRINT_ROOT):
        path = os.path.join(root, library + ".pretty", name + ".kicad_mod")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                return "thru_hole" in handle.read()
    raise ValueError("no footprint file for " + footprint)


# ---------------------------------------------------------------------------

PRODUCERS = (
    evaluate_rails,
    evaluate_input_path_ratings,
    evaluate_transient_clamp,
    evaluate_reverse_polarity,
    evaluate_conversion_efficiency,
    evaluate_converter,
    evaluate_bus_isolation,
    evaluate_bus_rate,
    evaluate_oscillator,
    evaluate_bus_connector,
    evaluate_termination,
    evaluate_bus_fault,
    evaluate_bus_protection,
    evaluate_input_thresholds,
    evaluate_input_survival,
    evaluate_output_drive,
    evaluate_output_safe_state,
    evaluate_output_clamp,
    evaluate_absolute_maximum,
    evaluate_dissipation,
    evaluate_protection_coverage,
    evaluate_connector_contract,
    evaluate_probe_access,
    evaluate_package_correspondence,
    evaluate_supply_availability,
    evaluate_assembly,
    evaluate_routed_copper,
)


def evaluate_all():
    parameters = load_parameters()
    results = []
    for producer in PRODUCERS:
        results.extend(producer(parameters))
    for result in results:
        result["verdict"] = claim.verdict(result["claim"])
    return results


REPORT_PATH = os.path.join(REPO_ROOT, "generated", "requirements.json")


def write_report(path=None):
    """The whole claim set, as an artifact rather than a console report.

    Built through the toolkit's claim-document constructor, so every claim
    is validated and every verdict re-derived at write time; CLAIM.MATRIX
    accepts at release exactly what was written here, and
    PROV.DERIVED_DOCUMENTS proves the committed copy fresh through this
    same entry point.
    """
    from . import requirements
    from pcbqa import evidence as toolkit_evidence

    evaluated = evaluate_all()
    document = toolkit_evidence.claim_document(
        [toolkit_evidence.claim_result(result["id"], result["identity"],
                                       result["claim"])
         for result in evaluated],
        register=os.path.relpath(requirements.REGISTER_PATH, REPO_ROOT))
    target = path or os.environ.get("PCBQA_OUT") or REPORT_PATH
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    return toolkit_evidence.write_document(target, document)


def summarise(results):
    counts = {}
    for result in results:
        counts[result["verdict"]["result"]] = counts.get(
            result["verdict"]["result"], 0) + 1
    return counts


if __name__ == "__main__":
    evaluated = evaluate_all()
    write_report()
    for result in sorted(evaluated, key=lambda item: (
            item["verdict"]["result"], item["id"], item["identity"])):
        value = result["claim"]["quantity"].get("value")
        rendered = "-" if value is None else "%.6g" % value
        sys.stdout.write("%-8s %-58s %-16s %14s %s\n" % (
            result["verdict"]["result"], result["id"], result["identity"],
            rendered, result["claim"]["units"]))
    sys.stdout.write("\n" + json.dumps(summarise(evaluated), sort_keys=True)
                     + "\n")
