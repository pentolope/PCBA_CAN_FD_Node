"""What each part turns into heat, and the junction path it has for it.

The board already judged dissipation against the package ratings its
datasheets print at 25 C. That answers a different question from the one an
installation asks: this node is rated to 60 C ambient, and a rating printed
at 25 C says nothing about what a part may dissipate continuously there.

So the parts that dissipate are declared here with the two figures that
decide it - the junction maximum and the steady-state junction-to-ambient
resistance - and the toolkit derives the continuous limit rather than
reading a headline. Both figures come from `components/parameters.json`,
which cites the frozen datasheet each was read from; nothing here types a
number a document does not carry.

Three parts are declared, and the ones left out are left out for a reason
that is stated rather than implied:

* the low-side switches (Q2-Q5, WST6066A) and the blocking FET (Q1,
  NCE6003X) publish a junction-to-ambient resistance measured "t<10sec" on
  a 1 inch2 2 oz test board. That is a transient figure. These channels
  conduct continuously, and applying a ten-second resistance to a part that
  is on for hours is exactly the substitution this declaration exists to
  prevent - so no steady-state path is claimed for them, their dissipation
  stays judged against the package rating as it already is, and the
  register's `within_the_package_dissipation` entry keeps saying a thermal
  analysis is still owed;
* the passives dissipate against their own power ratings, which
  `evaluate_dissipation` already checks part by part.
"""
from __future__ import annotations

import json
import sys

from . import netlist, rules

#: The ambient every statement in this module is made at: the highest the
#: board's ratings are claimed at, not a bench temperature.
AMBIENT_C = netlist.AMBIENT_MAX_C

#: The parts whose junction-to-ambient resistance the datasheet states for a
#: steady state, with the test board it was measured over where the document
#: names one. `measured_on` carries no copper area on purpose: neither
#: datasheet states the copper its figure was measured over, and a JEDEC
#: board is four layers where this board is two, so the junction claim comes
#: out as the conditional margin rather than a temperature this board never
#: measured.
THETA_CONTEXT = {
    "U2": {
        "measured_on": {
            "standard": "JESD51-7",
            "copper_layers": 4,
            "note": "high-K board under natural convection, obtained by "
                    "simulation in the JESD51-2a environment",
        },
        "detail": "this board is two layers and the figure was obtained "
                  "on a four-layer JEDEC board, which is why what "
                  "follows is a margin against that path rather than "
                  "a junction temperature for this one",
    },
    "U3": {
        "measured_on": {
            "standard": "JESD51-7",
            "copper_layers": 4,
            "note": "the four-layer construction the figure's own stated "
                    "condition names",
        },
        "detail": "this board is two layers and the figure was obtained "
                  "on a four-layer JEDEC board, which is why what "
                  "follows is a margin against that path rather than "
                  "a junction temperature for this one",
    },
    "U4": {
        # No measured_on: the datasheet gives one theta per package and
        # names no test board at all. Silence is recorded as silence.
        "detail": "the datasheet states one figure per package and no test "
                  "board, so there is nothing to compare this board's "
                  "copper against",
    },
}


def _document(record):
    return record["document"]


def _theta_ja(parameters, reference):
    """The steady-state junction-to-ambient path, as the toolkit wants it."""
    spec = rules._spec(parameters, reference)
    record = spec["thermal"]["rthja_c_per_w"]
    context = THETA_CONTEXT[reference]
    theta = {
        "value": record["value"],
        "units": "C/W",
        "source": "components/parameters.json: %s.thermal.rthja_c_per_w"
                  % rules._mpn(reference),
        "document": _document(record),
    }
    if record.get("condition"):
        theta["conditions"] = record["condition"]
    if "measured_on" in context:
        theta["measured_on"] = dict(context["measured_on"])
    return theta


def _junction_max_c(parameters, reference):
    return rules._spec(parameters, reference)["thermal"]["tj_max_c"]["value"]


def transceiver_dissipation_w(supply, parameters):
    """The transceiver drawing its dominant-state maximum on both supplies.

    An upper bound twice over: the bus is never dominant for the whole of
    every frame, and part of the dominant supply current leaves through the
    bus load and dissipates in the terminators rather than in the package.
    Neither correction is taken, because taking one would need a duty cycle
    and a bus model this board does not have.
    """
    spec = rules._spec(parameters, "U2")
    return (supply.intermediate_rail_max_v
            * spec["supply_current_max_a"]["value"]
            + supply.logic_rail_max_v
            * spec["io_supply_current_max_a"]["value"])


def converter_dissipation_w(supply):
    """The whole converter loss, charged to the controller.

    The inductor and the catch diode take a share of it that no measurement
    here separates, so charging all of it to the controller is an upper
    bound on the controller's own dissipation - and the efficiency it comes
    from is the deliberately pessimistic 75 percent the rail claims already
    use, which the bench measurement listed as an open dependency will
    replace with a measured figure.
    """
    output_w = (supply.intermediate_rail_max_v
                * supply.intermediate_current_max_a)
    return output_w * (1.0 / supply.converter_efficiency - 1.0)


def regulator_dissipation_w(supply):
    """The linear stage, dropping one rail to the next at the logic load.

    The same expression the `linear_stage_within_its_package_dissipation`
    claim is made from, at the same worst case: the intermediate rail at its
    maximum, the logic rail at its minimum, and the logic rail carrying its
    bounded maximum load.
    """
    return ((supply.intermediate_rail_max_v - supply.logic_rail_min_v)
            * supply.logic_current_max_a)


def parts(parameters):
    """The dissipation inventory, part by part, with its junction path."""
    supply = rules.Supply(parameters)
    watts = {
        "U2": transceiver_dissipation_w(supply, parameters),
        "U3": converter_dissipation_w(supply),
        "U4": regulator_dissipation_w(supply),
    }
    why = {
        "U2": "dominant-state supply current on both rails, taken as "
              "continuous; the share that leaves through the bus load is "
              "not subtracted",
        "U3": "the whole converter loss at the assumed 75 percent "
              "efficiency, charged to the controller rather than split "
              "with the inductor and the catch diode",
        "U4": "the drop from the intermediate rail to the logic rail at "
              "the logic rail's bounded maximum load",
    }
    document = {
        reference: sorted({
            _document(rules._spec(parameters,
                                  reference)["thermal"]["rthja_c_per_w"]),
            _document(rules._spec(parameters,
                                  reference)["thermal"]["tj_max_c"])})
        for reference in watts
    }
    return {
        reference: {
            "dissipation_w": watts[reference],
            "junction_max_c": _junction_max_c(parameters, reference),
            "theta_ja": _theta_ja(parameters, reference),
            "documents": document[reference],
            "detail": THETA_CONTEXT[reference]["detail"],
            "why": why[reference],
        }
        for reference in sorted(watts)
    }


def document(parameters=None):
    """The manifest's thermal block."""
    if parameters is None:
        parameters = rules.load_parameters()
    return {
        "ambient_c": AMBIENT_C,
        "why":
            "the three parts with a steady-state junction-to-ambient figure "
            "in their datasheets. The low-side switches and the blocking "
            "FET are not here: their datasheets state a junction-to-ambient "
            "resistance measured over ten seconds on a 1 inch2 2 oz board, "
            "which is not a continuous path, and this board will not derate "
            "a continuously conducting channel against a transient figure. "
            "Their dissipation stays judged against the package rating, and "
            "the register still records that a thermal analysis is owed for "
            "them. The passives are judged individually against their own "
            "power ratings.",
        "parts": parts(parameters),
    }


if __name__ == "__main__":
    json.dump(document(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
