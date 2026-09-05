"""What kind of statement each requirement is, and how it is established.

Until this register existed, all 225 of this board's claims recorded their
requirement source as the bare string ``BRIEF.md`` - the brief's demands,
the thresholds this design derived from datasheets, and the bounds it
simply chose all read as though the brief had stated them, and the two
choices the brief explicitly left open survived only in code comments. So
every requirement name a claim uses is registered here with its kind, what
it was derived from, why, the alternatives where it was a choice, the
verification methods that establish it, and the methods still required to
close it. The statements section carries the declarations and assumptions
no numeric claim is judged against - including the open choices, closed on
the record.

The register document builds through the toolkit's validating
constructors; REQ.REGISTER re-validates the committed file (per-kind
rules and origin resolution included) and REQ.CLAIM_JOIN enforces the
join with the claim set totally in both directions, at every validate
and release.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PATH = os.path.join(REPO_ROOT, "constraints", "requirements.json")
TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa import evidence  # noqa: E402

BRIEF = "BRIEF.md"

USER = evidence.USER_REQUIREMENT
DERIVED = evidence.DERIVED_REQUIREMENT
ASSUMPTION = evidence.ASSUMPTION
DECISION = evidence.DESIGN_DECISION
KINDS = evidence.STATEMENT_KINDS

(STATIC, GEOMETRY, ANALYTIC, CIRCUIT_SIM, DIGITAL_SIM, EXTRACTED,
 EM_SIM, THERMAL_SIM, MANUFACTURING_CHECK, PHYSICAL_TEST,
 DOCUMENTATION) = evidence.VERIFICATION_METHODS
METHODS = evidence.VERIFICATION_METHODS

#: Brief clauses, as the anchors a reader can follow.
FUNCTION = BRIEF + "#functional-requirements"
POWER = BRIEF + "#power-input-and-protection"
CAN = BRIEF + "#can-interface-and-termination"
IO = BRIEF + "#digital-inputs-and-low-side-outputs"
LAYOUT = BRIEF + "#placement-and-layout"
BRING_UP = BRIEF + "#test-and-bring-up"
OPEN = BRIEF + "#open-choices"


def _user(statement, clause, verified_by, still_required=()):
    return {"kind": USER, "statement": statement, "derived_from": (clause,),
            "origin": clause, "verified_by": verified_by,
            "still_required": tuple(still_required)}


def _derived(statement, clause, origin, rationale, verified_by,
             still_required=()):
    return {"kind": DERIVED, "statement": statement,
            "derived_from": (clause,) if isinstance(clause, str)
            else tuple(clause),
            "origin": origin, "rationale": rationale,
            "verified_by": verified_by,
            "still_required": tuple(still_required)}


def _decision(statement, rationale, alternatives, verified_by,
              still_required=()):
    return {"kind": DECISION, "statement": statement, "rationale": rationale,
            "alternatives_considered": tuple(alternatives),
            "verified_by": verified_by,
            "still_required": tuple(still_required)}


# ---------------------------------------------------------------------------
# the requirements every claim is judged against

REGISTER = {

    # --- rails and supply compatibility -------------------------------------

    "at_or_above_the_transceiver_supply_minimum": _derived(
        "the intermediate rail stays at or above the transceiver's supply "
        "minimum at the tolerance corner that lowers it",
        POWER, "tcan1042_ti",
        "the brief requires that 'the transceiver shall get the supply "
        "voltage its datasheet requires'; the datasheet window's lower edge "
        "is the requirement, evaluated with the converter's reference and "
        "the feedback divider at their worst corner",
        (ANALYTIC,)),

    "at_or_below_the_transceiver_supply_maximum": _derived(
        "the intermediate rail stays at or below the transceiver's supply "
        "maximum at the tolerance corner that raises it",
        POWER, "tcan1042_ti",
        "the same datasheet window's upper edge, evaluated at the opposite "
        "corner of the reference and divider tolerances",
        (ANALYTIC,)),

    "at_or_above_the_controller_supply_minimum": _derived(
        "the logic rail stays at or above the controller's characterised "
        "supply minimum",
        POWER, "stm32g431_st",
        "the brief demands working rails without naming figures; the "
        "figures are the controller datasheet's characterised window",
        (ANALYTIC,)),

    "at_or_below_the_controller_supply_maximum": _derived(
        "the logic rail stays at or below the controller's characterised "
        "supply maximum",
        POWER, "stm32g431_st",
        "the upper edge of the same characterised window, at the top of "
        "the regulator's accuracy",
        (ANALYTIC,)),

    "at_or_above_the_transceiver_interface_minimum": _derived(
        "the logic rail stays at or above the transceiver's I/O supply "
        "minimum",
        POWER, "tcan1042_ti",
        "the transceiver's logic-side interface has its own supply window, "
        "separate from its bus-side supply; both have to be met for the "
        "controller and transceiver to exchange levels",
        (ANALYTIC,)),

    "above_the_regulator_floor": _derived(
        "the intermediate rail stays above the logic rail's maximum plus "
        "the regulator's declared dropout bound",
        POWER, "ht75rxx_holtek",
        "the linear regulator only regulates while its input clears its "
        "output by its dropout; the datasheet states dropout only at 1 mA, "
        "so the figure used is this design's declared bound at the logic "
        "load - an assumption registered separately",
        (ANALYTIC,), still_required=(PHYSICAL_TEST,)),

    "within_the_regulator_output_rating": _derived(
        "the logic rail's bounded worst-case load stays within the "
        "regulator's output current rating",
        POWER, "ht75rxx_holtek",
        "the load bound sums the controller at its datasheet maximum, the "
        "transceiver's interface supply, the indicator and the rail bleed",
        (ANALYTIC,)),

    "within_the_converter_output_rating": _derived(
        "the intermediate rail's bounded worst-case load stays within the "
        "converter's output current rating",
        POWER, "mp2459_mps",
        "the load bound takes the transceiver driving a dominant bit into "
        "the lowest load its datasheet characterises, continuously, plus "
        "everything behind the regulator",
        (ANALYTIC,)),

    # --- input path, reverse polarity, transients ----------------------------

    "above_the_declared_input_maximum": _derived(
        "every part standing across the input rail or in the path from it "
        "is rated above the declared input maximum",
        POWER, "design_netlist",
        "the brief requires 'every part in that path rated above it with "
        "margin' over a stated range; the range is this design's "
        "declaration (18-30 V, registered as a statement), and each part's "
        "rating is read from its own frozen datasheet",
        (ANALYTIC, DOCUMENTATION)),

    "at_or_above_the_declared_input_maximum": _derived(
        "every clamp's stand-off voltage covers the declared input maximum "
        "so protection never conducts in normal operation",
        POWER, "smaj_mdd",
        "a clamp whose stand-off sits below the working rail conducts "
        "continuously; the brief's protection requirements imply a "
        "stand-off floor at the declared maximum",
        (ANALYTIC,)),

    "equals_the_declared_transient_clamp": _derived(
        "the declared transient clamp level equals the fitted input "
        "suppressor's maximum clamping voltage at its rated pulse current",
        POWER, "smaj_mdd",
        "the brief requires transients 'clamped below the rating of "
        "everything behind the input'; the level everything is compared "
        "against must be the fitted part's own worst figure, not a chosen "
        "number, or the comparison floats free of the hardware",
        (DOCUMENTATION,)),

    "above_the_clamping_voltage": _derived(
        "every part the transient reaches while the input clamp conducts "
        "is rated above the clamp's maximum clamping voltage",
        POWER, "smaj_mdd",
        "'clamped below the rating of everything behind the input', "
        "inverted per part: the highest level the clamp can present is its "
        "clamping voltage at rated pulse current, and each exposed part's "
        "rating must clear it",
        (ANALYTIC,)),

    "within_the_gate_source_rating": _derived(
        "the reverse-blocking device's gate clamp holds its gate-source "
        "voltage within the device's rating at the top of the zener "
        "tolerance",
        POWER, "nce6003x_nce",
        "the brief requires reverse polarity 'shall not damage the board "
        "or latch'; the blocking FET's gate sees the zener's clamp level, "
        "and the worst case for the rating is the zener's maximum",
        (ANALYTIC,)),

    "at_or_above_a_characterised_drive": _derived(
        "each FET gate is driven at or above a gate-source voltage its "
        "on-resistance is characterised at",
        POWER, "wst6066a_winsok",
        "an on-resistance is only a datasheet fact at the gate drive the "
        "datasheet characterises; every drop computed from it requires the "
        "gate to actually reach that point",
        (ANALYTIC,)),

    "within_the_zener_power_rating": _derived(
        "the gate-clamp zener's dissipation at the declared input maximum "
        "stays within its power rating",
        POWER, "bzt52c12_mdd",
        "the clamp carries the divider current whenever the input is up; "
        "its steady dissipation is bounded at the declared maximum with "
        "the series element at its low tolerance corner",
        (ANALYTIC,)),

    # --- conversion ---------------------------------------------------------

    "below_a_quarter_of_the_whole_input_to_output_difference_at_load":
        _decision(
        "the linear stage dissipates less than a quarter of what "
        "dissipating the whole input-to-output difference at load would",
        "the brief forbids dissipating the full input-to-output difference "
        "at load; 'not the full difference' needs a checkable margin, and "
        "a quarter is the bound this design declares. The switched "
        "topology beats it by construction - the only linear element "
        "drops the intermediate-to-logic difference, never input-to-logic",
        ("checking merely 'less than the whole difference', which any "
         "working converter satisfies vacuously and which would therefore "
         "judge nothing",),
        (ANALYTIC,)),

    "within_the_package_dissipation": _derived(
        "no package dissipates more than its datasheet rating with every "
        "channel conducting at once",
        IO, "wst6066a_winsok",
        "the brief requires the stated per-channel current 'with all four "
        "on'; the package figures used are the datasheet ratings at their "
        "own 25 C reference, so this establishes dissipation against the "
        "rating, not a junction temperature",
        (ANALYTIC,), still_required=(THERMAL_SIM,)),

    "below_the_inductor_saturation_current": _derived(
        "the converter's peak inductor current stays below the inductor's "
        "saturation rating at the tolerance corner that maximises ripple",
        POWER, "ind_swpa5040_sunlord",
        "an inductor past saturation stops being the part the converter's "
        "stability and current limit were computed with; the peak is the "
        "load bound plus half the worst-corner ripple",
        (ANALYTIC,)),

    "below_the_inductor_heat_rating_current": _derived(
        "the converter's DC output current stays below the inductor's "
        "heat-rating current",
        POWER, "ind_swpa5040_sunlord",
        "the thermal rating bounds continuous current; the DC component "
        "alone is compared, and the omitted ripple share is recorded on "
        "the claim",
        (ANALYTIC,)),

    "below_the_converter_current_limit": _derived(
        "the converter's peak current stays below its own minimum current "
        "limit",
        POWER, "mp2459_mps",
        "a peak that reaches the limit turns the limit into the regulator; "
        "the design point stays below the datasheet's minimum limit so "
        "regulation is by feedback, not by the protection",
        (ANALYTIC,)),

    "within_the_diode_average_current_rating": _derived(
        "the catch diode's average current at worst duty stays within its "
        "forward-current rating",
        POWER, "b1100_diodes",
        "the diode conducts for the off fraction of each cycle; its "
        "average current is the output current times that fraction at the "
        "corner that maximises it",
        (ANALYTIC,)),

    "above_the_enable_threshold": _derived(
        "the converter's enable divider clears its rising threshold at the "
        "declared input minimum",
        POWER, "mp2459_mps",
        "an enable that does not clear its threshold at the input minimum "
        "is a board that does not start inside its declared range; the "
        "datasheet states only a typical threshold, which the claim "
        "records as its assumption",
        (ANALYTIC,)),

    "within_the_converter_pin_rating": _derived(
        "the enable pin stays within its absolute maximum while the input "
        "is at the transient clamp level",
        POWER, "mp2459_mps",
        "the enable divider sees the clamped transient; the pin's absolute "
        "maximum has to cover the divider's output at that level at the "
        "corner that raises it",
        (ANALYTIC,)),

    # --- the bus ------------------------------------------------------------

    "no_controller_pin_on_a_bus_conductor": _user(
        "no controller pin lands on CANH or CANL; the controller reaches "
        "the bus only through the transceiver",
        FUNCTION, (STATIC,)),

    "bus_conductors_adjacent_with_nothing_between": _user(
        "CANH and CANL occupy adjacent contacts of the bus connector with "
        "no other contact between them",
        CAN, (STATIC,)),

    "at_or_below_the_transceiver_qualified_rate": _derived(
        "the declared data-phase rate stays at or below the rate the "
        "fitted transceiver variant's bit-timing specification supports",
        FUNCTION, "tcan1042_ti",
        "the brief requires 'the maximum qualified data-phase rate "
        "stated'; the stated rate (registered as a statement) is qualified "
        "against the G-variant datasheet's minimum transmitted bit time",
        (ANALYTIC, DOCUMENTATION)),

    "within_the_declared_oscillator_budget": _decision(
        "the crystal's worst-case frequency error, pulling included, stays "
        "within the declared per-node tolerance budget",
        "no CAN specification clause is frozen in this repository that "
        "states a tolerance for this rate, so the board declares one: the "
        "classical requirement that two nodes' clocks not drift more than "
        "a fraction of a bit over the longest unsynchronised stretch, "
        "halved per node. Initial tolerance, temperature, one year of "
        "ageing and the load network's pulling are summed arithmetically",
        ("adopting a vendor application note's figure, which is not frozen "
         "evidence in this repository and could not be cited",),
        (ANALYTIC,)),

    "within_the_controller_oscillator_range": _derived(
        "the crystal's frequency sits inside the controller's supported "
        "external-oscillator range",
        FUNCTION, "stm32g431_st",
        "the controller's clock tree supports a stated HSE range; a "
        "crystal outside it is a part the reference manual does not "
        "describe",
        (DOCUMENTATION,)),

    "within_the_controller_maximum_critical_transconductance": _derived(
        "the crystal's critical transconductance, computed at its worst "
        "resistance and capacitance corner, stays within the controller's "
        "stated maximum",
        FUNCTION, "xtal_8mhz_yxc",
        "the controller can only start a crystal whose critical "
        "transconductance is inside what its oscillator can supply; "
        "whether a gain margin beyond the stated maximum is required is a "
        "vendor application-note question this board does not resolve, so "
        "oscillator start-up remains a physical test",
        (ANALYTIC,), still_required=(PHYSICAL_TEST,)),

    # --- termination --------------------------------------------------------

    "within_five_percent_of_the_nominal_termination": _decision(
        "the enabled termination presents the nominal 120 ohm differential "
        "load within five percent at every tolerance corner",
        "the brief requires 'a nominal 120 ohm differential load' without "
        "a tolerance; a nominal needs a checkable window. Five percent "
        "holds the two-leg stack at every corner of the fitted parts' "
        "tolerance and is declared once, so a substitution that widened "
        "the stack would fail here instead of shipping",
        ("judging only the bare resistor tolerance stack, which would "
         "silently widen with any part substitution",),
        (ANALYTIC,)),

    "each_termination_leg_passes_through_its_own_link": _derived(
        "each termination leg passes through its own removable link, one "
        "per side of the pair",
        CAN, "design_netlist",
        "the brief requires termination 'switchable to fully removed "
        "without unsoldering parts'; with a split termination that is only "
        "true if BOTH legs break - pulling both links removes the "
        "differential load rather than leaving one line loaded against "
        "the centre capacitor",
        (STATIC,)),

    "within_the_link_current_rating": _derived(
        "the termination links carry their normal and bus-fault currents "
        "within the link's contact rating",
        CAN, "jumper_shunt_boomele",
        "the links sit in the differential path, so the dominant drive "
        "current and the bounded bus-fault current both pass through "
        "them; a contact rated below either is a switch that fails "
        "closed",
        (ANALYTIC,)),

    # --- bus faults and protection ------------------------------------------

    "above_the_declared_bus_fault_voltage": _derived(
        "the transceiver and the bus protector each stand off the declared "
        "bus fault voltage",
        CAN, "tcan1042_ti",
        "the brief requires the withstood fault voltage to be stated and "
        "to cover a bus line shorted to ground or to the node's own 24 V; "
        "the declared figure is the input range's maximum, and both parts "
        "on the bus must stand it off",
        (ANALYTIC,)),

    "below_the_transceiver_bus_fault_rating": _derived(
        "the bus protector clamps below the transceiver's own fault "
        "rating",
        CAN, "esdcan05_st",
        "a protector that clamps above what the transceiver survives "
        "protects nothing; the clamp ceiling is the transceiver's fault "
        "rating",
        (ANALYTIC,)),

    "at_or_above_the_declared_discharge_level": _derived(
        "the bus protector and the transceiver are each rated at or above "
        "the declared IEC 61000-4-2 contact discharge level",
        CAN, "esdcan05_st",
        "the brief requires meeting 'the declared IEC 61000-4-2 level'; "
        "the level is this design's declaration (8 kV contact, powered, "
        "registered as a statement), and both documents state "
        "device-level ratings - a system discharge result for this board "
        "remains a physical test",
        (DOCUMENTATION,), still_required=(PHYSICAL_TEST,)),

    "below_a_tenth_of_a_picofarad": _decision(
        "the bus protector's line-to-line capacitance mismatch stays below "
        "a tenth of a picofarad",
        "the brief requires protection 'balanced line to line' without a "
        "number; a tenth of a picofarad is the bound this design declares, "
        "met by fitting one dual device whose datasheet states the "
        "variation between its own two lines - a figure the datasheet "
        "gives as a typical, which the claim records",
        ("two discrete single-line devices, whose mismatch would be the "
         "difference of two independent parts' tolerances and could not "
         "be bounded to this level from their datasheets",),
        (DOCUMENTATION,)),

    "within_the_declared_bus_capacitance_budget": _decision(
        "the protection adds no more capacitance to the bus than five "
        "percent of a data-phase bit time through the transceiver's "
        "characterised load",
        "the brief requires protection to 'add no more capacitance than "
        "the qualified rate allows'; what the rate allows is not a frozen "
        "specification figure, so the board declares the budget: five "
        "percent of a bit time at the declared data-phase rate through "
        "the load the transceiver's datasheet characterises its outputs "
        "into",
        ("adopting a cable-system capacitance allocation from a CAN "
         "standard, which is not frozen evidence in this repository",),
        (ANALYTIC,)),

    "every_entering_conductor_carries_a_clamp_or_a_recorded_reason":
        _derived(
        "every conductor entering the board reaches a suppressor, or is "
        "recorded exempt with a reason",
        [POWER, CAN], "design_netlist",
        "the brief demands ESD protection at the bus connector and "
        "transient protection on the input; the design generalises that "
        "discipline to every entering conductor so an unprotected line is "
        "a named decision, never an omission",
        (STATIC,)),

    # --- field inputs -------------------------------------------------------

    "at_or_below_the_minimum_declared_input_supply": _derived(
        "each input's guaranteed on threshold at the terminal sits at or "
        "below the minimum declared supply",
        IO, "stm32g431_st",
        "the brief requires a stated threshold; for the input to read an "
        "asserted line at the bottom of the declared range, the "
        "worst-corner on threshold must sit at or below it",
        (ANALYTIC,)),

    "above_a_fifth_of_the_nominal_supply": _decision(
        "each input's guaranteed off threshold at the terminal stays above "
        "a fifth of the minimum declared supply",
        "the brief requires a stated threshold but no floor; a fifth of "
        "the minimum supply keeps the off level far enough from the "
        "reference that ground shift and coupled noise on field wiring "
        "cannot read as asserted",
        ("no floor at all, which would accept a divider whose off level "
         "sits in the millivolts and reads noise as signal",),
        (ANALYTIC,)),

    "at_least_one_volt_at_the_terminal": _decision(
        "each input's guaranteed hysteresis, referred to the terminal, is "
        "at least one volt",
        "the brief requires stated hysteresis but no figure; one volt at "
        "the terminal is the bound this design declares, computed from "
        "the controller's guaranteed threshold separation referred back "
        "through the divider rather than from the datasheet's typical "
        "hysteresis figure",
        ("relying on the controller's typical hysteresis, which is not a "
         "guaranteed figure and vanishes in the divider ratio",),
        (ANALYTIC,)),

    "every_input_has_a_pull_down_to_the_reference": _derived(
        "every input divider returns to the reference so an open terminal "
        "reads de-asserted",
        IO, "design_netlist",
        "the brief requires 'a defined state with its terminal open'; the "
        "mechanism is each divider's lower element returning to the "
        "reference, which is a checkable netlist fact",
        (STATIC,)),

    "within_the_controller_input_voltage_rating": _derived(
        "each input pin stays within its rating at the positive extreme of "
        "the declared range",
        IO, "stm32g431_st",
        "the brief requires each input to survive the maximum rated input "
        "continuously; on the positive side the clamp diode holds the pin "
        "one forward drop above the logic rail, which must sit inside the "
        "pin's tolerant-input rating",
        (ANALYTIC,)),

    "within_the_controller_injection_limit": _derived(
        "each input's negative-extreme injection stays within the "
        "controller's per-pin limit",
        IO, "stm32g431_st",
        "on the negative side the controller's own structure clamps the "
        "pin at the reference and the series element bounds the injected "
        "current, which must stay inside the datasheet's per-pin "
        "injection limit",
        (ANALYTIC,)),

    "within_the_controller_total_injection_limit": _derived(
        "the sum of every input's injection stays within the controller's "
        "total injection limit",
        IO, "stm32g431_st",
        "the per-pin limit is not the whole story: the datasheet also "
        "bounds the total, and the worst case is every input at the "
        "negative extreme at once",
        (ANALYTIC,)),

    "within_what_the_rail_bleed_alone_sinks": _derived(
        "the input clamps' worst-case back-fed current is less than what "
        "the rail bleed alone sinks",
        IO, "res_uniroyal",
        "with the board unpowered and every input at the positive "
        "extreme, the clamp diodes feed the logic rail; the bleed element "
        "must sink all of it or the rail floats up on an unpowered board",
        (ANALYTIC,)),

    "below_the_controller_supply_absolute_maximum": _derived(
        "the unpowered logic rail, lifted by the input clamps against the "
        "bleed, stays below the controller's absolute-maximum supply",
        IO, "stm32g431_st",
        "the same unpowered case bounds where the rail settles: the clamp "
        "current through the bleed's high tolerance corner must leave the "
        "rail below the controller's absolute maximum",
        (ANALYTIC,)),

    # --- field outputs ------------------------------------------------------

    "below_the_switch_threshold_voltage": _derived(
        "each output gate, with nothing driving it, stays below the "
        "switch's minimum threshold",
        IO, "wst6066a_winsok",
        "the brief requires every output 'off from power-on until "
        "firmware drives it'; after reset the controller leaves the port "
        "floating, so the pull-down must hold the gate below the FET's "
        "minimum threshold against the pin's leakage",
        (ANALYTIC,)),

    "each_gate_reaches_one_switch_and_its_own_pull_down": _derived(
        "each output gate net reaches exactly one switch and its own "
        "pull-down to the reference",
        IO, "design_netlist",
        "the brief requires outputs that 'switch independently' and are "
        "off from power-on; the netlist condition is one switch and one "
        "pull-down per gate net, shared with nothing",
        (STATIC,)),

    "within_the_switch_continuous_current": _derived(
        "each channel's rated current stays within the switch's "
        "continuous drain rating",
        IO, "wst6066a_winsok",
        "the declared per-channel rating (registered as a statement) must "
        "sit inside the FET's continuous current rating for the channel "
        "rating to be the board's and not the transistor's",
        (ANALYTIC,)),

    "below_the_switch_breakdown_voltage": _derived(
        "the output clamp's maximum clamping voltage stays below the "
        "switch's minimum breakdown",
        IO, "smf_jingdao",
        "the brief requires inductive turn-off clamped within the "
        "switch's rating; the clamp's worst clamping voltage at rated "
        "pulse current is what the drain sees, and it must clear the "
        "FET's minimum breakdown",
        (ANALYTIC,)),

    # --- the field supply path ----------------------------------------------

    "at_or_above_the_sum_of_the_channel_ratings": _derived(
        "the resettable fuse holds the sum of the channel ratings at the "
        "declared maximum ambient",
        IO, "pptc_1812l200_lute",
        "all four channels at their rated current pass the fuse; its hold "
        "current is read from the datasheet's derating table at the "
        "declared ambient, not interpolated",
        (ANALYTIC, DOCUMENTATION)),

    "above_the_sum_of_the_channel_ratings": _derived(
        "the field connector's contact rating covers the sum of the "
        "channel ratings",
        IO, "term_db128v_dorabo",
        "the field return concentrates every channel's current in the "
        "connector; its rating must clear the sum",
        (ANALYTIC, DOCUMENTATION)),

    "within_the_fuse_maximum_fault_current": _derived(
        "the declared prospective fault current stays within the fuse's "
        "maximum interrupt rating",
        POWER, "pptc_1812l200_lute",
        "the board's own series resistance is milliohms, so the fault "
        "current a short draws is set by the installation; the board "
        "declares the prospective current the installation must respect "
        "(registered as a statement), and the fuse must be rated for it",
        (ANALYTIC, DOCUMENTATION)),

    "within_one_volt_of_the_declared_input_minimum": _decision(
        "the field supply at the connector stays within one volt of the "
        "declared input minimum at full load",
        "the brief requires parts rated over a stated range but sets no "
        "budget for what the board's own path may drop; one volt at full "
        "load is the bound this design declares, spent across the fuse, "
        "the blocking device and the board's copper - first priced from "
        "the copper budget, then re-checked against the routed copper's "
        "extracted resistance",
        ("no declared drop budget, which would let the board consume the "
         "field devices' margin invisibly",),
        (ANALYTIC, EXTRACTED)),

    "within_the_declared_board_copper_budget": _derived(
        "each field conductor's extracted resistance stays within the "
        "declared board copper budget",
        LAYOUT, "board_extraction",
        "every pre-layout rail claim priced the board's conductors from a "
        "declared budget because no copper existed yet; the routed "
        "copper's traced resistance is compared back against that budget "
        "so the price paid is checked rather than trusted",
        (EXTRACTED,)),

    "within_the_budgeted_copper_drop": _derived(
        "each output conductor's drop at its rated current stays within "
        "the budgeted copper drop",
        LAYOUT, "board_extraction",
        "the same check per channel: the extracted conductor resistance "
        "times the rated channel current against the budget times that "
        "current",
        (EXTRACTED,)),

    "the_extraction_was_taken_from_the_committed_board": _derived(
        "the committed extraction describes the committed board file, by "
        "digest",
        LAYOUT, "board_extraction",
        "every copper claim reads the extraction; if the board was edited "
        "after the trace, those claims describe copper that is no longer "
        "there, so the digest match is the first claim and gates the rest",
        (STATIC,)),

    # --- structure, contracts, access ---------------------------------------

    "every_connector_pin_carries_its_declared_function": _derived(
        "every connector pin lands on the net its declared contract names",
        CAN, "design_netlist",
        "the connector contracts are the design's declaration of what "
        "mates with what; a pin on the wrong net is a mating failure the "
        "netlist can catch before any board exists",
        (STATIC,)),

    "equals_the_declared_position_count": _derived(
        "each connector's physical position count matches its declared "
        "pin order",
        CAN, "term_db128v_dorabo",
        "a contract declaring more or fewer positions than the part has "
        "is a contract about a different connector",
        (STATIC, DOCUMENTATION)),

    "equals_the_package_terminal_count": _derived(
        "each footprint's pad count matches its package's terminal count",
        LAYOUT, "design_netlist",
        "a land pattern with the wrong pad count cannot carry the "
        "package; the count is compared against each part's land-pattern "
        "document",
        (STATIC, DOCUMENTATION)),

    "every_terminal_named_by_a_package_map_is_on_a_net_or_declared_"
    "no_connect": _derived(
        "every terminal a package map names is on a net or declared "
        "no-connect",
        LAYOUT, "design_netlist",
        "a mapped terminal on no net is either a missing connection or a "
        "missing declaration; both are defects the netlist can name",
        (STATIC,)),

    "every_required_net_reaches_a_probe": _user(
        "every rail, both bus lines and the transceiver's TXD/RXD pair "
        "reach a test point",
        BRING_UP, (STATIC,)),

    "matches_the_declared_through_hole_count": _derived(
        "the number of through-hole parts matches the declared assembly "
        "policy",
        IO, "design_netlist",
        "through-hole count drives the hand-soldering line of the "
        "assembly quote; the policy (registered as a statement) declares "
        "it so the quote is priced from the design, not discovered",
        (STATIC, MANUFACTURING_CHECK)),

    "at_or_above_the_planned_build_quantity": _derived(
        "the catalogue's recorded stock covers the planned build quantity "
        "for every ordered part",
        OPEN, "jlcpcb_catalogue_snapshot",
        "the planned build (registered as a statement) is a requirement "
        "on availability, not only on the design; the stock figure is the "
        "catalogue reading at its recorded retrieval date, not a "
        "reservation",
        (DOCUMENTATION,)),

    # --- ratings sweeps -----------------------------------------------------

    "above_the_steady_level_across_the_part": _derived(
        "every capacitor is rated above the highest steady level across "
        "it",
        POWER, "design_netlist",
        "the net levels are bounded rail-by-rail from the supply model; "
        "transient levels are the clamp claims' business, and this sweep "
        "compares steady levels only",
        (ANALYTIC,)),

    "within_the_resistor_power_rating": _derived(
        "every resistor carrying steady current dissipates within its "
        "rating, and the termination legs survive a bus fault",
        POWER, "res_uniroyal",
        "each steady dissipation is bounded with the whole named level "
        "across the element, which overstates dividers; the termination "
        "legs are additionally bounded under the transceiver-limited bus "
        "fault",
        (ANALYTIC,)),
}


# ---------------------------------------------------------------------------
# statements no numeric claim is judged against

STATEMENTS = {

    "mcu_and_transceiver_selection": _decision(
        "the controller is an STM32G431 and the transceiver a TCAN1042 "
        "G-variant",
        "the brief leaves both open subject to an integrated CAN-FD "
        "controller, the declared I/O count, and the stated rate and "
        "fault ratings. The STM32G431 carries an FDCAN controller and "
        "enough I/O; the TCAN1042's G variant is the one whose datasheet "
        "specifies bit timing at a 200 ns transmitted bit, which is what "
        "qualifies the declared 5 Mbit/s data phase, and its fault "
        "rating covers the node's own 24 V shorted to a bus line",
        ("a transceiver without the G qualification, rejected because the "
         "declared data-phase rate could not be stated from its "
         "datasheet",
         "an MCU with external CAN controller, rejected as a second "
         "device and a second clock domain the brief's integrated-CAN-FD "
         "condition excludes",),
        (DOCUMENTATION,)),

    "termination_control": _decision(
        "termination switches manually, by two removable links, not under "
        "MCU control",
        "the brief leaves manual versus MCU-controlled switching open. "
        "Links satisfy 'switchable to fully removed without unsoldering "
        "parts' with zero switch elements in the differential path: an "
        "electronic switch would put its own resistance and capacitance "
        "into the termination and both would need their own "
        "qualification against the balance and capacitance bounds",
        ("an analog switch or relay under MCU control, rejected because "
         "its on-resistance sits inside the 120 ohm tolerance window and "
         "its capacitance inside the bus budget, both of which are "
         "already declared tight",),
        (STATIC,)),

    "input_range_declaration": _decision(
        "the declared continuous input range is 18 to 30 V",
        "the brief requires the continuous 24 V input range to be stated; "
        "18 V is what the field supply may sag to and still be inside the "
        "declared range, 30 V is what every part behind the terminal is "
        "rated above and what the input clamp stands off",
        ("a wider 9-36 V industrial range, rejected because the input "
         "clamp's stand-off and the converter's maximum rating would "
         "both need different parts",),
        (DOCUMENTATION,)),

    "channel_current_rating": _decision(
        "each field output is rated at 0.25 A with all four channels "
        "conducting at once",
        "the brief requires 'the stated per-channel current with all four "
        "on' but leaves the figure open; a quarter ampere per channel "
        "keeps the four-channel sum inside the resettable fuse's held "
        "current at the declared ambient with the fuse read from its "
        "derating table",
        ("a higher per-channel rating, rejected because the fuse's hold "
         "current at the declared ambient would not cover the sum",),
        (ANALYTIC,)),

    "maximum_ambient": _decision(
        "the board's ratings are claimed at a maximum ambient of 60 C",
        "the resettable fuse's hold current and the controller's supply "
        "current are both temperature-dependent; every figure used is "
        "read from its datasheet at or above this ambient, so the "
        "declared ambient is the temperature the ratings are actually "
        "established at",
        ("25 C, rejected as a bench figure that would overstate the "
         "fuse's held current in any real enclosure",),
        (DOCUMENTATION,)),

    "prospective_fault_current": _decision(
        "the installation must not present more than 30 A of prospective "
        "fault current at the board's terminals",
        "the fuse cannot be shown to survive more than its own maximum "
        "fault current, and the board's own series resistance is far too "
        "small to limit a stiff source; the board therefore declares the "
        "figure the installation has to respect rather than assuming a "
        "wiring resistance that would make the question go away",
        ("assuming a field-wiring resistance to bound the fault current, "
         "rejected because nothing in the design controls the wiring",),
        (DOCUMENTATION,), still_required=(PHYSICAL_TEST,)),

    "esd_level_declaration": _decision(
        "the declared bus discharge level is 8 kV IEC 61000-4-2 contact, "
        "powered",
        "the brief requires meeting 'the declared level' and leaves the "
        "level to the design; 8 kV contact is the level both fitted "
        "parts' datasheets state device ratings at or above",
        ("15 kV air discharge as the headline figure, rejected because "
         "contact discharge is the harsher and better-specified test at "
         "the same nominal level",),
        (DOCUMENTATION,)),

    "bus_rate_declaration": _decision(
        "the node is qualified at 1 Mbit/s arbitration and 5 Mbit/s data "
        "phase",
        "the brief requires the maximum qualified data-phase rate to be "
        "stated; the arbitration rate is the classical CAN ceiling, and "
        "the data-phase rate is the one the fitted transceiver variant's "
        "datasheet characterises",
        ("2 Mbit/s data phase, rejected as leaving qualified transceiver "
         "capability unstated for no margin gain",),
        (DOCUMENTATION,)),

    "assembly_policy": _decision(
        "assembly is one reflow of the front side, with the through-hole "
        "connectors hand-soldered and counted",
        "a single placement side and an explicit through-hole count keep "
        "the assembly quote priced from the design; the count is judged "
        "by its own claim",
        ("second-side placement, rejected because nothing on this board "
         "needs it and it adds a setup to the quote",),
        (MANUFACTURING_CHECK,)),

    "converter_efficiency_bound": {
        "kind": ASSUMPTION,
        "statement": "the converter's efficiency is at least 75 percent "
                     "at the loads this board presents",
        "reason": "the input-current bound every input-path figure uses "
                  "divides the output power by a deliberately pessimistic "
                  "efficiency; the datasheet's curves sit well above it "
                  "but are not frozen as parameters",
        "revisable": True,
        "invalidated_by": "a measured efficiency below 75 percent at the "
                          "board's own load, which would raise the input "
                          "current above the figures used",
        "verified_by": (PHYSICAL_TEST,),
        "still_required": (PHYSICAL_TEST,),
    },

    "regulator_dropout_bound": {
        "kind": ASSUMPTION,
        "statement": "the regulator's dropout at the logic-rail load is "
                     "within the declared bound used by the rail claims",
        "reason": "the datasheet states dropout only at 1 mA; the logic "
                  "load is higher, so the bound the intermediate rail is "
                  "judged against is a declared figure, not a datasheet "
                  "limit",
        "revisable": True,
        "invalidated_by": "a measured dropout above the declared bound at "
                          "the logic load, which would push the regulator "
                          "out of regulation inside the declared input "
                          "range",
        "verified_by": (PHYSICAL_TEST,),
        "still_required": (PHYSICAL_TEST,),
    },
}


#: Origins that are not frozen datasheets. Each names the file in the tree
#: the requirement is derived from, so a citation cannot point at nothing.
NON_DOCUMENT_ORIGINS = {
    "design_netlist": "design/netlist.py",
    "jlcpcb_catalogue_snapshot": "components/jlcpcb.json",
    "board_extraction": "generated/extraction.json",
}


def entry(name):
    try:
        return REGISTER[name]
    except KeyError:
        raise KeyError(
            "requirement %r is judged by a claim but is not registered in "
            "design/requirements.py; every requirement states what kind of "
            "statement it is" % (name,))


def source_of(name):
    """The string a claim records as its requirement's source.

    Kind first, so a reader of one claim can see whether the requirement
    came from the brief or from this design without opening the register.
    """
    record = entry(name)
    origin = record.get("origin", name)
    if not isinstance(origin, str):
        origin = "+".join(origin)
    return "%s:%s" % (record["kind"], origin)


def _entry(name, record):
    fields = dict(record)
    return evidence.requirement_entry(
        name, fields.pop("kind"), fields.pop("statement"),
        fields.pop("verified_by"),
        still_required=fields.pop("still_required", ()), **fields)


def document():
    return evidence.register_document(
        [_entry(name, record) for name, record in sorted(REGISTER.items())],
        [_entry(name, record)
         for name, record in sorted(STATEMENTS.items())],
        file_origins=NON_DOCUMENT_ORIGINS)


def write(path=None):
    target = path or os.environ.get("PCBQA_OUT") or REGISTER_PATH
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    return evidence.write_document(target, document())


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
