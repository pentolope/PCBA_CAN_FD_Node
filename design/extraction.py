"""What the routed copper actually is, measured from the routed board.

Every pre-layout claim about a field channel priced the board's own copper
from a budget, because at that point no copper existed. It exists now, so
the budget can stop being an assumption: each path is traced through the
copper the board carries, and its resistance is computed from the traced
geometry and the physical inputs the fabricator states. What comes back is
bound to the board file by digest, so a board edited afterwards cannot keep
wearing this measurement.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

from . import layout, netlist, physical

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
BOARD_PATH = os.path.join(REPO_ROOT, netlist.PROJECT_NAME + ".kicad_pcb")
EXTRACTION_PATH = os.path.join(REPO_ROOT, "generated", "extraction.json")

if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa import extract, geom, headless  # noqa: E402


#: Copper plating thickness assumed for a via barrel. The fabricator's
#: approved capabilities state finished copper for the layers and say
#: nothing about the hole wall, so this is an assumption and is written
#: thin: IPC-6012 class 2 asks for 20 um average, and a barrel thinner than
#: it is assumed to be is a barrel with more resistance than it has, which
#: is the direction an upper bound has to err in.
VIA_PLATING_THICKNESS_MM = 0.018

#: Annealed copper at 20 C, the same figure the traversal is priced with.
RESISTIVITY_OHM_M = extract.IACS_RESISTIVITY_OHM_M


def via_barrel_resistance_ohm(board_thickness_mm):
    """One through via's barrel, as a bound rather than a model.

    The traversal prices track copper and states that it omits the vias it
    crosses, which leaves every path resistance a lower bound. This is what
    turns it back into an upper bound: a barrel the length of the board, of
    the drill's diameter, plated to the thickness assumed above.
    """
    radius_mm = layout.VIA_DRILL_MM / 2.0
    area_mm2 = math.pi * ((radius_mm + VIA_PLATING_THICKNESS_MM) ** 2
                          - radius_mm ** 2)
    return (RESISTIVITY_OHM_M * (board_thickness_mm / 1000.0)
            / (area_mm2 / 1.0e6))


def paths():
    """The traversals whose resistance a claim depends on.

    The field supply and the four field outputs, each from the part that
    limits it to the contact the field wiring lands on: those are the
    conductors a channel's whole current runs through, and the only ones
    whose copper resistance a pre-layout claim had to guess at.

    Each is named as a chain of pads rather than two endpoints, because
    each of these conductors deliberately runs through a pad on its way -
    the field supply through its probe, an output through its clamp - and a
    pad is an electrical node. A model that traced straight past one would
    be charging the current for copper the pad shorts out.
    """
    traced = [(netlist.FIELD_SUPPLY_NET, ("F1.2", "TP2.1", "J3.1"))]
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        traced.append(("DO%d" % channel,
                       ("Q%d.3" % (channel + 1), "D%d.1" % (channel + 8),
                        "J3.%d" % (channel + 1))))
    return tuple(traced)


def board_digest():
    hasher = hashlib.sha256()
    with open(BOARD_PATH, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def chord_error_mm():
    """How finely a curved shape is approximated, from the board's own
    geometry profile: the tolerance the physical gates are already judged
    with, so an extraction cannot quietly work to a different one."""
    with open(os.path.join(REPO_ROOT, "board", "manifest.json"), "r",
              encoding="utf-8") as handle:
        document_ = json.load(handle)
    tolerance = document_["geometry_profile"]["tolerances"][
        "polygon_chord_error_mm"]
    return tolerance["value"]


def document():
    headless.suppress_blocking_ui()
    geom.configure(chord_error_mm())
    import pcbnew
    inputs = physical.document()
    copper = inputs["copper_thickness_mm"]
    board = pcbnew.LoadBoard(BOARD_PATH)
    per_via = via_barrel_resistance_ohm(
        inputs["board_thickness_mm"]["value"])
    records = []
    for net, chain in paths():
        hops = [extract.path_resistance(board, net, first, second, copper)
                for first, second in zip(chain, chain[1:])]
        records.append({
            "kind": "board-path-dc-chain",
            "net": net,
            "pads": list(chain),
            "hops": hops,
            "path_length_mm": round(
                sum(hop["path_length_mm"] for hop in hops), 6),
            "resistance_ohm": round(
                sum(hop["resistance_claim"]["quantity"]["value"]
                    for hop in hops), 9),
            "resistance_uncertainty_ohm": round(
                sum(hop["resistance_uncertainty_ohm"] for hop in hops), 9),
            "via_count_in_path": sum(hop["via_count_in_path"]
                                     for hop in hops),
            "via_barrel_allowance_ohm": round(
                per_via * sum(hop["via_count_in_path"] for hop in hops), 9),
            "meaning": "series DC resistance from the first pad to the last, "
                       "summed over the hops between the pads the conductor "
                       "runs through; each hop is its own path-scoped "
                       "traversal and carries its own claim",
        })
    return {
        "kind": "board-path-dc-extraction",
        "board_file": os.path.basename(BOARD_PATH),
        "board_file_sha256": board_digest(),
        "physical_inputs": inputs,
        "via_barrel_resistance_ohm": {
            "value": round(per_via, 9),
            "units": "ohm",
            "basis": "assumed",
            "assumption": "a through barrel the board's own thickness, of "
                          "the declared drill diameter, plated %g mm - the "
                          "fabricator's approved capabilities state finished "
                          "copper for the layers and nothing about the hole "
                          "wall" % VIA_PLATING_THICKNESS_MM,
        },
        "paths": records,
        "notes": [
            "geometry-derived DC resistance only; no inductance and no "
            "capacitance is claimed here",
            "the board file digest above is what these numbers describe; a "
            "board edited afterwards is a different board",
        ],
    }


def simulation_models():
    """The extracted models a post-layout scenario names, by alias.

    This IS the validation gate's own assembly - the shared entry point
    `pcbqa.sim.assemble.extracted_models` - not a reimplementation of it,
    so a scenario run outside the gate gets the same numbers by
    construction rather than by inspection. The physical inputs are the
    committed `fab/physical_inputs.json` records, validated the way the
    gate validates them.
    """
    from pcbqa.core import load_manifest
    from pcbqa.sim import assemble

    headless.suppress_blocking_ui()
    manifest = load_manifest(os.path.join(REPO_ROOT, "board",
                                          "manifest.json"))
    return assemble.extracted_models(manifest)


def simulation_registry():
    """The registry the gate judges scenarios with, by construction."""
    from pcbqa.core import load_manifest
    from pcbqa.sim import assemble

    headless.suppress_blocking_ui()
    manifest = load_manifest(os.path.join(REPO_ROOT, "board",
                                          "manifest.json"))
    return assemble.registry_for(manifest)


def load():
    with open(EXTRACTION_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resistances():
    """Measured path resistance by net, as an upper bound.

    A claim built on this must not be built on the middle of a symmetric
    ambiguity nor on a traversal that priced no via, so what is handed out
    is the traced resistance with the junction ambiguity and the bounded
    barrels of every via the path crosses added to it.
    """
    measured = {}
    for record in load()["paths"]:
        measured[record["net"]] = (record["resistance_ohm"]
                                   + record["resistance_uncertainty_ohm"]
                                   + record["via_barrel_allowance_ohm"])
    return measured


def write(path=None):
    target = path or os.environ.get("PCBQA_OUT") or EXTRACTION_PATH
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return target


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
