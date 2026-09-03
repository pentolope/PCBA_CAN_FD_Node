"""Circuit scenarios, and what each one is allowed to establish.

Five questions the schematic can answer before any copper exists.

  * All four field outputs switching on at once is a step the supply, its
    wiring, the resettable fuse and the reverse-blocking device all have to
    carry. Where the field supply and the converter's input land while it
    happens is the question, and every element between them is a passive
    whose value a datasheet states.
  * A field input is a divider with a filter on it, and the filter is what
    gives the input its noise immunity. How long the receiver then takes to
    see a terminal change is arithmetic the requirement report bounds by hand
    and this solves.
  * The same input at the top of its declared range is held by a clamp to the
    logic rail. What the controller pin actually sees there decides whether
    the input survives, and the network is linear once the clamp is a source.
  * Every output gate and the transceiver's mode pin have to sit where they
    belong with nothing driving them, which is the state a controller that
    has not started leaves them in.
  * The bus conductor the driver has to move carries the protection, the
    termination and whatever the cable adds. Whether it settles inside a
    data-phase bit is what the declared rate rests on.

The elements are resistors, capacitors and ideal sources, because that is
what the scenario contract accepts; every device that is not one of those is
a declared stand-in, and each stand-in says what it replaces.

Two questions are deliberately absent. Nothing here asks what the converter's
control loop does: a linear network cannot represent a switching regulator's
response, and a stand-in resistance for it is not a conservative model but a
different circuit - one with no feedback at all. What the intermediate rail
does under a load step therefore stays a physical test, and the requirement
report states the rail's limits from the converter's own regulation instead.
And no scenario claims a discharge result: an IEC 61000-4-2 event is not a
linear network problem, and the board's discharge claims rest on device
ratings and on a physical test.
"""
from __future__ import annotations

import json
import os
import sys

from . import netlist, rules

REPO_ROOT = rules.REPO_ROOT
SIM_DIR = os.path.join(REPO_ROOT, "sim")

#: How long the input side is watched after the four field outputs switch on.
LOAD_STEP_WINDOW_S = 2.0e-3

#: A budget, not a measurement: resistance of the supply and its wiring up to
#: the input terminal. It is what the field load step is dropped across, and
#: a stiffer supply only makes the answer better.
SUPPLY_WIRING_BUDGET_OHM = 0.2

#: Series resistance of one side of the transceiver's bus driver, bounded
#: from its own datasheet: a Thevenin source whose open-circuit differential
#: output is the datasheet maximum into a near-open load and which still
#: reaches the datasheet minimum into the load it is characterised at.
def _driver_series_ohm(parameters):
    bus = rules._spec(parameters, "U2")["bus"]
    open_circuit_v = bus["differential_output_dominant_open_max_v"]["value"]
    loaded_min_v = bus["differential_output_dominant_min_v"]["value"]
    load_ohm = bus["characterised_load_ohm"]["value"]
    differential_ohm = load_ohm * (open_circuit_v / loaded_min_v - 1.0)
    return differential_ohm / 2.0


def _parameters():
    return rules.load_parameters()


def _sum_capacitance(*nets, derate=True):
    """Every capacitor on the named nets, at the low end of its tolerance.

    Low, because every question these scenarios ask is about a rail falling
    or an edge arriving late, and less capacitance answers both worse.
    """
    parameters = _parameters()
    total = 0.0
    for net in nets:
        for pin_ref in netlist.NETS[net]:
            reference = pin_ref.split(".", 1)[0]
            if not reference.startswith("C"):
                continue
            value = rules._capacitance_farads(reference)
            if derate:
                tolerance = parameters["parts"][netlist.PARTS[reference][
                    "mpn"]]["capacitor"]["tolerance"]["value"]
                value *= 1.0 - tolerance
            total += value
    return total


def _ideal(records):
    return {name: {"stands_in_for": detail,
                   "accepted_for_design_decision": True}
            for name, detail in records.items()}


def _measurement(name, kind, node, op=None, value=None, knowledge=None):
    record = {"name": name, "kind": kind, "node": node}
    if op is not None:
        record["assertion"] = {"op": op, "value": value}
    if knowledge is not None:
        record["knowledge"] = knowledge
    return record


def _pulse(v1, v2, period_s, delay_s=None):
    delay = period_s / 20.0 if delay_s is None else delay_s
    return {"v1": v1, "v2": v2, "delay_s": delay,
            "rise_s": period_s / 1.0e6, "fall_s": period_s / 1.0e6,
            "width_s": period_s / 2.0, "period_s": period_s}


# ---------------------------------------------------------------------------

def field_load_step_scenario(parameters):
    """All four field outputs switching on at once, from the input alone."""
    supply = rules.Supply(parameters)
    converter = rules._spec(parameters, "U3")["converter"]
    fuse = rules._spec(parameters, "F1")["resettable_fuse"]
    blocking = rules._spec(parameters, "Q1")["fet"]
    step_a = supply.field_current_a
    quiescent_a = supply.converter_input_current_max_a
    return {
        "name": "field_outputs_switching_on_together",
        "description": "every field output turns on at once at its rated "
                       "current, and the field supply and the converter's "
                       "input are watched while the step lands",
        "elements": [
            {"kind": "vsource_dc", "name": "SUPPLY",
             "nodes": ["source", "return"],
             "value": supply.input_min_v},
            {"kind": "resistor", "name": "RWIRE",
             "nodes": ["source", "terminal"],
             "value": SUPPLY_WIRING_BUDGET_OHM},
            {"kind": "resistor", "name": "RBLOCK", "nodes": ["return", "0"],
             "value": blocking["rds_on_ohm"]["10"]["value"]},
            {"kind": "capacitor", "name": "CIN", "nodes": ["terminal", "0"],
             "value": _sum_capacitance(netlist.INPUT_RAIL_NET)},
            {"kind": "resistor", "name": "RLOGIC", "nodes": ["terminal", "0"],
             "value": supply.input_min_v / quiescent_a},
            {"kind": "resistor", "name": "RFUSE",
             "nodes": ["terminal", "field"],
             "value": fuse["resistance_max_ohm"]["value"]},
            {"kind": "resistor", "name": "RFIELD", "nodes": ["field", "sink"],
             "value": supply.input_min_v / step_a},
            {"kind": "vsource_pulse", "name": "SWITCHON",
             "nodes": ["sink", "0"],
             "pulse": _pulse(supply.input_min_v, 0.0, 2 * LOAD_STEP_WINDOW_S,
                             delay_s=LOAD_STEP_WINDOW_S / 20.0)},
        ],
        "analyses": [{"kind": "tran", "step_s": LOAD_STEP_WINDOW_S / 2000.0,
                      "stop_s": LOAD_STEP_WINDOW_S}],
        "measurements": [
            _measurement("field_supply_minimum", "tran_min_voltage", "field",
                         ">=", netlist.INPUT_SUPPLY["min_v"] - 1.0),
            _measurement("converter_input_minimum", "tran_min_voltage",
                         "terminal", ">=",
                         converter["input_voltage_min_v"]["value"]),
        ],
        "assumptions": _ideal({
            "SUPPLY": "the external supply at the bottom of the declared "
                      "input range, as an ideal source",
            "RWIRE": "the supply and its wiring as the declared budget; a "
                     "stiffer supply drops less",
            "RBLOCK": "the reverse-blocking device as its datasheet "
                      "on-resistance at the gate drive its clamp gives it; "
                      "it sits in the return, which is where this element "
                      "sits too",
            "CIN": "every capacitance on the input rail as one ideal "
                   "capacitor at the low end of its tolerance, with no ESR "
                   "and no ESL - the reservoir is an electrolytic whose ESR "
                   "the omission of makes the dip shallower than it is",
            "RLOGIC": "the converter's input draw as a fixed resistance at "
                      "the bounded maximum",
            "RFUSE": "the resettable fuse at its maximum resistance one hour "
                     "after reflow",
            "RFIELD": "all four field outputs at their rated current at "
                      "once, as one resistance sized at the declared input "
                      "minimum",
            "SWITCHON": "the instant every output is enabled together, as an "
                        "ideal switch; firmware that staggers them sees "
                        "less than this",
        }),
    }


def input_edge_scenario(parameters):
    """A field input crossing the receiver's threshold after the terminal."""
    supply = rules.Supply(parameters)
    stage = rules.InputStage(parameters, 1)
    mcu = rules._spec(parameters, "U1")
    vih = (mcu["digital_inputs"]["vih_min"]["fraction_of_supply"]["value"]
           * supply.logic_rail_max_v)
    vil = (mcu["digital_inputs"]["vil_max"]["fraction_of_supply"]["value"]
           * supply.logic_rail_min_v)
    filter_f = (rules._capacitance_farads("C21")
                * (1.0 + rules._capacitor_tolerance(parameters, "C21")))
    pin_f = mcu["pin_capacitance_f"]["value"]
    window_s = netlist.INPUT_RESPONSE_TIME_S
    return {
        "name": "field_input_edge_through_its_divider_and_filter",
        "description": "one field input driven from the bottom of the "
                       "declared supply range, through the divider, the "
                       "filter and the series element that feeds the "
                       "controller pin",
        "elements": [
            {"kind": "vsource_pulse", "name": "FIELD",
             "nodes": ["terminal", "0"],
             "pulse": _pulse(0.0, netlist.INPUT_SUPPLY["min_v"],
                             2 * window_s, delay_s=window_s / 20.0)},
            {"kind": "resistor", "name": "RUPPER",
             "nodes": ["terminal", "divider"],
             "value": stage.upper * (1.0 + stage.tolerance)},
            {"kind": "resistor", "name": "RLOWER", "nodes": ["divider", "0"],
             "value": stage.lower * (1.0 - stage.tolerance)},
            {"kind": "capacitor", "name": "CFILTER",
             "nodes": ["divider", "0"], "value": filter_f},
            {"kind": "resistor", "name": "RSERIES",
             "nodes": ["divider", "pin"],
             "value": stage.series * (1.0 + stage.tolerance)},
            {"kind": "capacitor", "name": "CPIN", "nodes": ["pin", "0"],
             "value": pin_f},
        ],
        "analyses": [{"kind": "tran", "step_s": window_s / 4000.0,
                      "stop_s": window_s}],
        "measurements": [
            _measurement("receiver_high_level", "tran_max_voltage", "pin",
                         ">=", vih),
            _measurement("receiver_low_level", "tran_min_voltage", "pin",
                         "<=", vil),
        ],
        "assumptions": _ideal({
            "FIELD": "a field signal at the bottom of the declared supply "
                     "range, as an ideal source with no series resistance of "
                     "its own; a real field driver is slower and the wiring "
                     "adds resistance",
            "RUPPER": "the upper divider element at the top of its "
                      "tolerance, which charges the filter slowest",
            "RLOWER": "the lower divider element at the bottom of its "
                      "tolerance, which lowers the level the pin reaches",
            "CFILTER": "the input filter at the top of its tolerance, which "
                       "is the slowest, with no dielectric loss and no DC "
                       "bias derating",
            "RSERIES": "the series element that bounds injection, at the top "
                       "of its tolerance",
            "CPIN": "the controller pin's own capacitance at the datasheet's "
                    "typical, which is the only figure it states",
        }),
    }


def input_overrange_scenario(parameters):
    """A field input at the top of its declared range, held by its clamp."""
    supply = rules.Supply(parameters)
    stage = rules.InputStage(parameters, 1)
    mcu = rules._spec(parameters, "U1")
    diode = rules._spec(parameters, "D5")["diode"]
    clamp_v = (supply.logic_rail_max_v
               + diode["forward_voltage_max_v"]["0.001"]["value"])
    return {
        "name": "field_input_at_the_top_of_its_declared_range",
        "description": "one field input at the declared maximum with its "
                       "clamp to the logic rail conducting, and what the "
                       "controller pin sees",
        "elements": [
            {"kind": "vsource_dc", "name": "FIELD", "nodes": ["terminal", "0"],
             "value": netlist.INPUT_SUPPLY["max_v"]},
            {"kind": "resistor", "name": "RUPPER",
             "nodes": ["terminal", "divider"],
             "value": stage.upper * (1.0 - stage.tolerance)},
            {"kind": "resistor", "name": "RLOWER", "nodes": ["divider", "0"],
             "value": stage.lower * (1.0 + stage.tolerance)},
            {"kind": "vsource_dc", "name": "CLAMP", "nodes": ["clamp", "0"],
             "value": clamp_v},
            {"kind": "resistor", "name": "RCLAMP",
             "nodes": ["divider", "clamp"], "value": 1.0},
            {"kind": "resistor", "name": "RSERIES",
             "nodes": ["divider", "pin"],
             "value": stage.series * (1.0 - stage.tolerance)},
        ],
        "analyses": [{"kind": "op"}],
        "measurements": [
            _measurement("controller_pin_level", "op_voltage", "pin", "<=",
                         mcu["input_voltage_ft_max_v"]["value"]),
            _measurement("divider_node_level", "op_voltage", "divider"),
        ],
        "assumptions": _ideal({
            "FIELD": "the field terminal at the declared maximum, as an "
                     "ideal source",
            "RUPPER": "the upper divider element at the bottom of its "
                      "tolerance, which drives the most into the clamp",
            "RLOWER": "the lower divider element at the top of its tolerance",
            "CLAMP": "the logic rail at the top of the regulator's accuracy "
                     "plus the clamp diode's datasheet forward voltage, as "
                     "an ideal source: a diode is not a linear element and "
                     "the rail it clamps to is held by the regulator",
            "RCLAMP": "the clamp's dynamic resistance, small enough that the "
                      "node sits at the declared clamp level; the datasheet "
                      "states none",
            "RSERIES": "the series element that bounds injection, at the "
                       "bottom of its tolerance",
        }),
    }


def safe_state_scenario(parameters):
    """Every gate and the transceiver's mode pin with nothing driving them."""
    supply = rules.Supply(parameters)
    mcu = rules._spec(parameters, "U1")
    fet = rules._spec(parameters, "Q2")["fet"]
    transceiver = rules._spec(parameters, "U2")
    leakage_ohm = (supply.logic_rail_max_v
                   / mcu["input_leakage_max_a"]["value"])
    standby_ohm = (supply.logic_rail_max_v
                   / transceiver["digital_inputs"][
                       "standby_pull_up_current_max_a"]["value"])
    standby_threshold_v = (
        transceiver["digital_inputs"]["vil_max"]["fraction_of_supply"][
            "value"] * supply.logic_rail_min_v)
    return {
        "name": "gates_and_mode_pin_with_nothing_driving_them",
        "description": "an output gate and the transceiver's mode input in "
                       "the state a controller that has not started leaves "
                       "them, with each one's pull-down against the only "
                       "current there is",
        "elements": [
            {"kind": "vsource_dc", "name": "RAIL", "nodes": ["rail", "0"],
             "value": supply.logic_rail_max_v},
            {"kind": "resistor", "name": "RLEAK", "nodes": ["rail", "pin"],
             "value": leakage_ohm},
            {"kind": "resistor", "name": "RSERIES", "nodes": ["pin", "gate"],
             "value": rules._resistor_ohms("R26")},
            {"kind": "resistor", "name": "RPULLDOWN", "nodes": ["gate", "0"],
             "value": rules._resistor_ohms("R30")},
            {"kind": "resistor", "name": "RSTBYUP", "nodes": ["rail", "stby"],
             "value": standby_ohm},
            {"kind": "resistor", "name": "RSTBYDOWN", "nodes": ["stby", "0"],
             "value": rules._resistor_ohms("R8")},
        ],
        "analyses": [{"kind": "op"}],
        "measurements": [
            _measurement("output_gate_voltage", "op_voltage", "gate", "<=",
                         fet["vgs_threshold_min_v"]["value"]),
            _measurement("transceiver_mode_voltage", "op_voltage", "stby",
                         "<=", standby_threshold_v),
        ],
        "assumptions": _ideal({
            "RAIL": "the logic rail at the top of the regulator's accuracy",
            "RLEAK": "the controller pin's own input leakage at the "
                     "datasheet maximum, as the resistance that sources it "
                     "from the rail; after reset every port is a floating "
                     "input, so that leakage is the only current there is",
            "RSERIES": "the gate's series element at its nominal value",
            "RPULLDOWN": "the gate's pull-down at its nominal value",
            "RSTBYUP": "the transceiver's own pull-up on its mode input, as "
                       "the resistance that sources its datasheet maximum "
                       "low-level input current from the interface supply",
            "RSTBYDOWN": "the mode pin's pull-down at its nominal value",
        }),
    }


def bus_edge_scenario(parameters):
    """One bus conductor settling into everything this board hangs on it."""
    supply = rules.Supply(parameters)
    transceiver = rules._spec(parameters, "U2")["bus"]
    protector = rules._spec(parameters, "D4")["suppressor"]
    bit_s = 1.0 / netlist.DATA_PHASE_RATE_BPS
    drive_v = (transceiver["differential_output_dominant_min_v"]["value"]
               / 2.0)
    load_f = (protector["capacitance_max_f"]["value"]
              + transceiver["input_capacitance_max_f"]["value"]
              + netlist.BUS_CABLE_CAPACITANCE_BUDGET_F)
    leg_ohm = rules._resistor_ohms("R9") * (
        1.0 + rules._resistor_tolerance(parameters, "R9"))
    settled_v = drive_v * netlist.BUS_SETTLED_FRACTION
    del supply
    return {
        "name": "bus_conductor_edge_into_its_own_load",
        "description": "one bus conductor driven at the declared data-phase "
                       "rate through the driver's own series resistance, "
                       "into the termination leg, the protection and the "
                       "capacitance the cable is budgeted for",
        "elements": [
            {"kind": "vsource_pulse", "name": "DRIVER",
             "nodes": ["drive", "0"],
             "pulse": _pulse(0.0, drive_v, 2 * bit_s,
                             delay_s=bit_s / 20.0)},
            {"kind": "resistor", "name": "RDRIVE", "nodes": ["drive", "bus"],
             "value": _driver_series_ohm(parameters)},
            {"kind": "resistor", "name": "RTERM", "nodes": ["bus", "0"],
             "value": leg_ohm},
            {"kind": "capacitor", "name": "CBUS", "nodes": ["bus", "0"],
             "value": load_f},
        ],
        "analyses": [{"kind": "tran",
                      "step_s": bit_s / 4000.0,
                      "stop_s": bit_s * netlist.BUS_SETTLING_FRACTION_OF_BIT}],
        "measurements": [
            _measurement("bus_settled_level", "tran_max_voltage", "bus",
                         ">=", settled_v * leg_ohm
                         / (leg_ohm + _driver_series_ohm(parameters))),
            _measurement("bus_released_level", "tran_min_voltage", "bus"),
        ],
        "assumptions": _ideal({
            "DRIVER": "one side of the transceiver's dominant drive, as an "
                      "ideal step at the declared data-phase rate; a real "
                      "driver has a finite slew the datasheet states only as "
                      "a typical",
            "RDRIVE": "the driver's own series resistance, bounded from its "
                      "datasheet: a Thevenin source that still reaches the "
                      "stated minimum differential output into the load the "
                      "datasheet characterises, having reached the stated "
                      "maximum into a near-open one",
            "RTERM": "this node's own termination leg at the top of its "
                     "tolerance, referred to the reference because the "
                     "centre capacitor holds the split node there at these "
                     "frequencies",
            "CBUS": "the protector, the transceiver's own bus pin and the "
                    "declared cable budget as one capacitance; the cable is "
                    "a budget, not a measurement, and no transmission line "
                    "is modelled",
        }),
    }


#: The aliases the manifest registers the board's own copper under. The
#: models behind them are measured from the board during validation rather
#: than read from a file, so a scenario naming one cannot be looking at
#: copper that has since been rerouted.
FIELD_SUPPLY_COPPER_MODELS = (
    ("MCOPPER1", "field_supply_copper_fuse_to_probe", "field", "probe"),
    ("MCOPPER2", "field_supply_copper_probe_to_contact", "probe", "contact"),
)


def post_layout_field_load_step_scenario(parameters):
    """The same load step, with the board's own copper in the path.

    The pre-layout scenario had every conductor ideal, because no conductor
    existed. This one is that scenario with one substitution: the field
    supply's copper, from the fuse to the contact the field wiring lands on,
    is the copper the routed board carries, traced from it and priced at the
    fabricator's own finished thickness. The rail is then watched at the
    contact rather than at the fuse, which is where a field device is
    actually connected, and the same requirement is asked of it.

    What is deliberately not substituted here is each output's own copper:
    the load in this scenario is all four channels lumped into one
    resistance, and pushing four channels' current through one channel's
    conductor would overstate it. That conductor carries a quarter of this
    current and is checked at its own rating in the requirement report.
    """
    from . import extraction
    measured = {record["net"]: record
                for record in extraction.load()["paths"]}
    allowance = measured[netlist.FIELD_SUPPLY_NET]["via_barrel_allowance_ohm"]
    document = field_load_step_scenario(parameters)
    document["name"] = "field_outputs_switching_on_together_post_layout"
    document["description"] = (
        "every field output turns on at once at its rated current, with the "
        "field supply's own copper between the fuse and the contact taken "
        "from the routed board")
    elements = []
    for element in document["elements"]:
        if element["name"] == "RFIELD":
            for name, alias, first, second in FIELD_SUPPLY_COPPER_MODELS:
                elements.append({"kind": "model_instance", "name": name,
                                 "nodes": [first, second], "model": alias})
            elements.append({"kind": "resistor", "name": "RVIA",
                             "nodes": ["barrel", "contact"],
                             "value": allowance})
            element = dict(element, nodes=["contact", "sink"])
        elements.append(element)
    document["elements"] = elements
    # One measurement, and it is the one layout can have changed: what the
    # contact the field wiring lands on is holding while every channel
    # switches on. The converter's own input is upstream of every conductor
    # substituted here, and adding series resistance can only raise it, so
    # asserting a floor on it from this deck would be asserting a floor from
    # a ceiling; the pre-layout scenario is where that floor is established.
    document["measurements"] = [
        _measurement(
            "field_supply_minimum", "tran_min_voltage", "contact",
            ">=", netlist.INPUT_SUPPLY["min_v"] - 1.0,
            knowledge={
                "kind": "lower_bound",
                "basis": {
                    "kind": "assumed",
                    "detail": "the deck carries at least the resistance the "
                              "board does - the traced copper plus a bounded "
                              "barrel for every via it crosses - and this "
                              "network's contact voltage falls as that "
                              "resistance rises, so the board cannot hold "
                              "the contact lower than this deck does. The "
                              "monotonicity is an argument about this "
                              "circuit rather than a template the tool "
                              "checks, which is why the basis is assumed",
                },
            }),
    ]
    # The copper models are not declared as assumptions: an assumption
    # records what an ideal primitive stands in for, and those two stand in
    # for nothing - they are the board's own conductors, measured, and what
    # they are allowed to establish is their own evidence's business. The
    # barrels are the exception, because the traversal states that it prices
    # none of the vias it crosses.
    document["assumptions"] = dict(
        document["assumptions"],
        **_ideal({"RVIA": "every via the field supply's copper crosses, as "
                          "one resistance bounded from the board's declared "
                          "thickness, drill and an assumed plating; the "
                          "traversal prices the tracks and states that it "
                          "prices no barrel, so without this the deck would "
                          "carry less resistance than the board does"}))
    return document


SCENARIOS = (
    ("pre_layout_field_load_step.json", field_load_step_scenario),
    ("pre_layout_input_edge.json", input_edge_scenario),
    ("pre_layout_input_overrange.json", input_overrange_scenario),
    ("pre_layout_safe_state.json", safe_state_scenario),
    ("pre_layout_bus_edge.json", bus_edge_scenario),
    ("post_layout_field_load_step.json",
     post_layout_field_load_step_scenario),
)


def documents():
    parameters = _parameters()
    return {name: builder(parameters) for name, builder in SCENARIOS}


def _write(path, document):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def write():
    return [_write(os.path.join(SIM_DIR, name), document)
            for name, document in sorted(documents().items())]


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
