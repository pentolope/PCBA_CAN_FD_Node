from __future__ import annotations

import json
import os
import sys

from . import layout, netlist, rules, sexpr

PART_NUMBER_FIELD = "MPN"

REFLOW_PASSES = 1
PEAK_TEMP_C = 245.0
CLEANING = "no_clean"
SIDES = ("top",)

WAIVER_ACCEPTED_BY = "fabrication order review"
WAIVER_REVIEW_BY = "2027-03-01"
WAIVER_REASON = ("hand-soldered after reflow and named in the process's own "
                 "hand_solder list, so this part is never carried through "
                 "the declared profile")

THROUGH_HOLE_PAD = "thru_hole"


_PAD_TYPES = {}


def _pad_types(footprint):
    if footprint not in _PAD_TYPES:
        directory, name = layout._footprint_dir(footprint)
        path = os.path.join(directory, name + ".kicad_mod")
        with open(path, "r", encoding="utf-8") as handle:
            tree = sexpr.parse(handle.read())
        _PAD_TYPES[footprint] = {str(pad[2])
                                 for pad in sexpr.find_all(tree, "pad")}
    return _PAD_TYPES[footprint]


def through_hole(reference):
    footprint = netlist.PARTS[reference]["footprint"]
    return THROUGH_HOLE_PAD in _pad_types(footprint)


def placed():
    return {reference: part for reference, part in netlist.PARTS.items()
            if part["on_board"]}


def components():
    return {reference: part for reference, part in placed().items()
            if part["mpn"]}


def furniture():
    return {reference: {} for reference, part in sorted(placed().items())
            if not part["mpn"]}


def hand_soldered():
    return sorted(reference for reference in components()
                  if through_hole(reference))


def _figures(parameters, mpn):
    return (parameters["parts"].get(mpn) or {}).get("assembly") or {}


def parts(parameters=None):
    if parameters is None:
        parameters = rules.load_parameters()
    hand = set(hand_soldered())
    records = {}
    for reference, part in sorted(components().items()):
        record = records.setdefault(part["mpn"], {})
        figures = _figures(parameters, part["mpn"])
        if "peak_temp_max_c" in figures:
            record["peak_temp_max_c"] = figures["peak_temp_max_c"]["value"]
        if "max_reflow_passes" in figures:
            record["max_reflow_passes"] = int(
                figures["max_reflow_passes"]["value"])
        if reference in hand:
            record["process"] = "hand_solder_only"
    return records


def process():
    return {
        "reflow_passes": REFLOW_PASSES,
        "peak_temp_c": PEAK_TEMP_C,
        "sides": list(SIDES),
        "cleaning": CLEANING,
        "hand_solder": hand_soldered(),
    }


def process_waivers(parameters=None):
    waivers = []
    for mpn, record in sorted(parts(parameters).items()):
        peak = record.get("peak_temp_max_c")
        if record.get("process") != "hand_solder_only" or peak is None:
            continue
        if peak >= PEAK_TEMP_C:
            continue
        waivers.append({
            "part": mpn,
            "requirement": "peak_temp",
            "reason": WAIVER_REASON,
            "accepted_by": WAIVER_ACCEPTED_BY,
            "review_by": WAIVER_REVIEW_BY,
        })
    return waivers


def document(parameters=None):
    if parameters is None:
        parameters = rules.load_parameters()
    return {
        "part_number_field": PART_NUMBER_FIELD,
        "process": process(),
        "parts": parts(parameters),
        "furniture": furniture(),
        "process_waivers": process_waivers(parameters),
        "paste": {"pads": []},
    }


if __name__ == "__main__":
    json.dump(document(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
