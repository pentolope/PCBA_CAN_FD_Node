"""The board's manifest, generated from the design source rather than typed.

The manifest is what the validator reads: which files are the design, which
gates are mandatory, what the connectors carry, what the stackup is. Every one
of those is already stated somewhere in this repository - in the netlist, in
the layout, in the fabrication requirements - and a manifest typed by hand is
a second copy of all of it that can drift from the first.

So it is generated. The pin maps come from the netlist's own connector
contract, the constraint floor from the design settings the board file is
written with, and the simulation stages from the scenarios that exist.
"""
from __future__ import annotations

import json
import os
import sys

from . import (assembly, build, layout, netlist, physical, simulation,
               thermal)

MANIFEST_PATH = os.path.join(layout.REPO_ROOT, "board", "manifest.json")

RELEASE_PROFILE_ID = "jlcpcb-2layer-assembled"

MANDATORY_GATES = (
    "ARCH.CONTENTS",
    "ARCH.PROVENANCE",
    "ASM.PROCESS",
    "BOM.NATIVE_PARITY",
    "CONTRACT.CONNECTOR",
    "CONTRACT.PLACEMENT",
    "CPL.NATIVE_PARITY",
    "DFA.PASTE",
    "DRC.AUTHORITATIVE",
    "DRC.CONSTRAINT_FLOOR",
    "DRC.NO_SUPPRESSED_RULES",
    "ERC.AUTHORITATIVE",
    "NET.REFERENCE_CONTINUITY",
    "NET.TOPOLOGY",
    "PROV.REPORT_FRESHNESS",
    "ROUTE.GEOMETRY_HYGIENE",
    "ROUTE.PROVENANCE",
    "ROUTE.TINY_SEGMENTS",
    "SIM.SCENARIOS",
    "SIM.STAGE_COVERAGE",
    "STACK.GERBER_PARITY",
    "STACK.NATIVE_VS_MANIFEST",
    "THERMAL.DERATING",
    "THERMAL.DISSIPATION",
    "THERMAL.JUNCTION",
    "VIA.ANNULUS_MASK_OVERLAP",
    "VIA.IN_PAD_CONTACT",
    "VIA.MASK_CLEARANCE_PROCESS",
    "VIA.MASK_CLEARANCE_TARGET",
    "VIA.NATIVE_GERBER_AGREEMENT",
)

REQUIRED_EVIDENCE = (
    "evidence/index.json",
    "fab/selection.json",
    "generated/requirements.json",
    "generated/routing.json",
)


#: The pitch each connector's own land pattern was drawn on, and the name
#: the contract goes by.
CONNECTOR_PITCH_MM = {"J1": 5.08, "J2": 5.08, "J3": 5.08, "J4": 5.08,
                      "J5": 2.54, "J6": 2.54, "J7": 2.54}
CONNECTOR_IDS = {"J1": "supply_input", "J2": "bus_connector",
                 "J3": "field_output_connector",
                 "J4": "field_input_connector",
                 "J5": "programming_header",
                 "J6": "termination_link_canh",
                 "J7": "termination_link_canl"}


def _connector_pitch(reference):
    return CONNECTOR_PITCH_MM[reference]


def _connector_id(reference):
    return CONNECTOR_IDS[reference]


def connector_contracts():
    """One contract per connector, from the netlist's own function map."""
    pin_net = netlist.pin_to_net()
    contracts = []
    for reference in sorted(netlist.CONNECTOR_FUNCTION_NETS,
                            key=lambda name: int(name[1:])):
        pins = {}
        for pin_ref, net in pin_net.items():
            owner, _, number = pin_ref.partition(".")
            if owner == reference:
                pins[number] = net
        contracts.append({
            "id": _connector_id(reference),
            "reference": reference,
            "required_positions": len(pins),
            "required_rows": 1,
            "required_pitch_mm": _connector_pitch(reference),
            "required_side": "front",
            "population": {"dnp": False, "exclude_from_bom": False},
            "pin_map": {number: pins[number]
                        for number in sorted(pins, key=int)},
        })
    return contracts


def placement_rules():
    """Groups the board must contain, counted rather than located.

    Each entry is a family the design source generates as a set; a board that
    lost one, or grew one, disagrees with the source that made it.
    """
    outputs = netlist.OUTPUT_COUNT
    inputs = netlist.INPUT_COUNT
    return [
        {"id": "FIELD_CONNECTORS",
         "reference_regex": r"^J[34]$", "count": 2},
        {"id": "TERMINATION_LINKS",
         "reference_regex": r"^J[67]$", "count": 2},
        {"id": "OUTPUT_SWITCHES",
         "reference_regex": r"^Q[2-5]$", "count": outputs},
        {"id": "OUTPUT_CLAMPS",
         "reference_regex": r"^D(9|1[0-2])$", "count": outputs},
        {"id": "OUTPUT_GATE_NETWORKS",
         "reference_regex": r"^R(2[6-9]|3[0-3])$", "count": 2 * outputs},
        {"id": "INPUT_CLAMPS",
         "reference_regex": r"^D[5-8]$", "count": inputs},
        {"id": "INPUT_DIVIDERS",
         "reference_regex": r"^R(1[4-9]|2[0-5])$", "count": 3 * inputs},
        {"id": "INPUT_FILTERS",
         "reference_regex": r"^C2[1-4]$", "count": inputs},
        {"id": "TERMINATION_LEGS",
         "reference_regex": r"^R(9|10)$", "count": 2},
        {"id": "PROBES",
         "reference_regex": r"^TP[1-9]$", "count": 9},
        {"id": "MOUNTING",
         "reference_regex": r"^H[1-4]$", "count": 4},
    ]


def net_topology_rules():
    """The routes whose topology is a requirement rather than a result.

    The bus pair reaches the transceiver on the front layer and takes no via
    on the way: a via in that path is a hole in the reference the pair's own
    return current runs over, and the layer it would change to is the one
    that reference pours on. Each field output is the same argument at lower
    frequency: one conductor carries the whole of a channel's current, and a
    via in it is a hole in the only path that current has. The converter's
    switch node is the third: it is the only conductor on the board whose
    voltage moves the whole input rail in nanoseconds, and a via in it would
    carry that edge to the far side of the reference the loop closes
    through.
    """
    return [
        {"id": "BUS_PAIR",
         "net_regex": r"^CAN[HL]$",
         "source_pad_regex": r"^J2\.[23]$",
         "load_pad_regex": r"^U2\.[67]$",
         "max_vias_per_net": 0,
         "permitted_layers": ["F.Cu"]},
        {"id": "FIELD_OUTPUT_PATHS",
         "net_regex": r"^DO\d$",
         "source_pad_regex": r"^Q[2-5]\.3$",
         "load_pad_regex": r"^J3\.[2-5]$",
         "max_vias_per_net": 0,
         "permitted_layers": ["F.Cu"]},
        {"id": "SWITCH_NODE",
         "net_regex": r"^SW_NODE$",
         "source_pad_regex": r"^U3\.6$",
         "load_pad_regex": r"^L1\.1$",
         "max_vias_per_net": 0,
         "permitted_layers": ["F.Cu"]},
    ]


#: The pair's two routes, connector contact to transceiver pin. The same
#: two conductors `BUS_PAIR` constrains to one layer and no vias, asked the
#: other half of the question: the topology rule says the pair does not
#: leave the front layer, and this says the reference stays under it while
#: it is there. A test binds the endpoints to the topology rule so the two
#: cannot drift apart.
BUS_PAIR_ROUTES = (
    ("can_h", "CANH", r"^J2\.3$", r"^U2\.7$"),
    ("can_l", "CANL", r"^J2\.2$", r"^U2\.6$"),
)

#: How much of one bus route may run with no reference conductor beneath
#: it, totalled over the route. Not a measurement of what the board does -
#: it is what the board will accept, and it is set by where the reference
#: cannot be rather than by what the router happened to leave:
#:
#: * the pour keeps its declared clearance around the bus connector's own
#:   through-hole pads, so the first stretch off the contact has no
#:   reference under it whatever the routing does - about 1.5 mm; and
#: * one back-layer conductor crosses under the pair near the transceiver,
#:   and the pour clears it on both sides - a 0.25 mm track with 0.2 mm
#:   clearance either side is 0.65 mm of interruption.
#:
#: 2.5 mm covers the connector's antipad and one crossing. It does not
#: cover two, and it does not cover a route that has wandered off the pour
#: altogether, which is the point: a limit that only ever restates the
#: measurement forbids nothing.
BUS_PAIR_MAX_UNREFERENCED_MM = 2.5


def reference_continuity():
    """Where the bus pair's return current is required to be.

    A differential pair's return is not a budget item that can be traded
    against something else - it is either under the pair or it is somewhere
    worse, adding loop area to a signal whose whole immunity argument rests
    on the two conductors seeing the same interference. The pour on the
    back layer is that reference, and this declaration is what makes "the
    pour is under the pair" a checked statement rather than an intention
    recorded in a comment.
    """
    return {
        "reference_nets": [netlist.GROUND_NET],
        "why":
            "the bus pair's return runs in the back-layer reference pour "
            "the whole way from the connector to the transceiver; the "
            "keepouts that hold that stretch of pour are drawn by the "
            "layout for this reason, and this is the check that they did",
        "paths": {
            name: {
                "max_unreferenced_mm": BUS_PAIR_MAX_UNREFERENCED_MM,
                "steps": [{"kind": "copper", "net": net,
                           "from": source, "to": load}],
            }
            for name, net, source, load in BUS_PAIR_ROUTES
        },
    }


def stackup_expected():
    """What each copper layer is for.

    The front layer pours the input rail and the field supply; the back
    layer pours the one reference every clamp on this board diverts into.
    The gate names one net per layer, so each entry names the one the layer
    exists for.
    """
    return [{"role": "plane", "plane_net": netlist.INPUT_RAIL_NET},
            {"role": "plane", "plane_net": netlist.GROUND_NET}]


def simulation_stages():
    """Each scenario under the stage its own file name declares.

    A scenario is pre-layout or post-layout by what it models, not by where
    it is listed, so the name it is written under is what decides - and a
    scenario whose name says neither is refused rather than filed under a
    guess.
    """
    stages = {}
    for name in sorted(simulation.documents()):
        stage = name.split("_field")[0].split("_input")[0] \
            .split("_safe")[0].split("_bus")[0]
        if stage not in ("pre_layout", "post_layout"):
            raise ValueError("scenario %r names no stage" % name)
        stages.setdefault(stage, []).append("sim/" + name)
    return stages


def extracted_models():
    """The board's own conductors, registered for a post-layout scenario.

    Each is measured from the board under validation rather than read from a
    file, so no scenario can be looking at copper that has since been
    rerouted. The field supply is declared in two hops because it runs
    through its probe's pad on the way, and a pad is an electrical node: a
    single traversal past one would charge the current for copper the pad
    shorts out.
    """
    return {
        "physical_inputs": "fab/physical_inputs.json",
        "paths": {
            "field_supply_copper_fuse_to_probe": {
                "net": netlist.FIELD_SUPPLY_NET,
                "from_pad": "F1.2", "to_pad": "TP2.1"},
            "field_supply_copper_probe_to_contact": {
                "net": netlist.FIELD_SUPPLY_NET,
                "from_pad": "TP2.1", "to_pad": "J3.1"},
        },
    }


def routing_search():
    """The candidate search the toolkit runs, with this loop's own figures.

    The reserved nets are the pours and the copper this repository draws
    because its geometry is a requirement: the reference, the two supply
    pours, the bus pair, the termination's centre, the switch node and
    the field outputs. 0.30 mm is the routing margin, not the rule: the
    router lands its diagonals short of the figure it works to, and the
    board is judged at the declared floor. `keep_input_copper` is what
    stops the router treating drawn copper as its own previous output
    and ripping the requirement out.
    """
    return {
        "nets": {"reserved": [netlist.GROUND_NET, netlist.INPUT_RAIL_NET,
                              netlist.FIELD_SUPPLY_NET,
                              netlist.SUPPLY_RETURN_NET,
                              "CANH", "CANL", "TERM_SPLIT", "SW_NODE"]
                 + ["DO%d" % channel
                    for channel in range(1, netlist.OUTPUT_COUNT + 1)]},
        "orderings": ["inside_out", "original", "mps"],
        "clearances_mm": [0.30],
        "attempts": 3,
        "grid_step_mm": 0.1,
        "options": {
            "track_width_mm": layout.TRACK_WIDTH_MM,
            "via_size_mm": layout.VIA_DIAMETER_MM,
            "via_drill_mm": layout.VIA_DRILL_MM,
            "board_edge_clearance_mm": 0.45,
            "hole_to_hole_clearance_mm": 0.3,
            "same_net_pad_clearance_mm": 0.3,
            "no_power_tap_neckdown": True,
            "keep_input_copper": True,
        },
        "acceptance": {
            "require_zero": ["errors", "warnings", "unconnected",
                             "schematic_parity"],
            # The full design gate class, so routing accepts nothing
            # release will reject.
            "gates": ["design"],
        },
    }


def routing_transforms():
    """The tidy passes a candidate takes before it is judged, by name.

    The same repairs this repository's own loop made, now run by the
    toolkit: `split_tees` is the junction split the checker needs, and
    every removal keeps only while connectivity is unchanged.
    """
    return {"passes": ["snap_to_via", "snap_to_pad_anchor",
                       "collapse_degenerate", "fold_subfloor",
                       "restore_widths", "restore_vias",
                       "split_tees", "dedupe", "prune"]}


def _base_document():
    project = netlist.PROJECT_NAME
    classes = {entry["name"]: {key: value
                               for key, value in entry.items()
                               if key != "name"}
               for entry in build.NET_CLASSES}
    return {
        "schema_version": 2,
        "board_id": project,
        "constraint_version": "layout-stage-2026-09-02",
        "project_root": "..",
        "tools": {"kicad_cli": "kicad-cli"},
        "sources": {
            "schematic": project + ".kicad_sch",
            "project": project + ".kicad_pro",
            "pcb": project + ".kicad_pcb",
        },
        "board_origin_mm": [0.0, 0.0],
        "documentation_globs": ["BRIEF.md"],
        "checks": {
            "erc": {"extra_flags": []},
            "drc": {
                "extra_flags": [],
                "forbidden_severities": ["ignore"],
                "permitted_ignored_rules": [],
                "constraint_floor": {
                    "rules": dict(build.DESIGN_RULES),
                    "net_classes": classes,
                },
            },
        },
        "waivers": [],
        "geometry_profile": {
            "version": "geom-1",
            "tolerances": {
                "waiver_location_mm": {"value": 0.001, "units": "mm"},
                "polygon_chord_error_mm": {"value": 0.001, "units": "mm"},
                "contact_mm": {"value": 1e-06, "units": "mm"},
                "coordinate_match_mm": {"value": 0.002, "units": "mm"},
                "rotation_match_deg": {"value": 0.1, "units": "deg"},
                "dimension_match_mm": {"value": 0.002, "units": "mm"},
                "clearance_match_mm": {"value": 0.01, "units": "mm"},
                "layer_symmetric_difference_mm2": {"value": 0.05,
                                                   "units": "mm2"},
            },
        },
        "stackup": {"expected": stackup_expected()},
        "placement_rules": placement_rules(),
        "net_topology": {"rules": net_topology_rules()},
        # Both pads faces carry parts on some of these boards and the
        # courtyard proof is cheap on either; the edge-clearance gate is
        # NOT declared here deliberately - this board places connectors
        # or mounting holes at the outline by design, so it cannot
        # truthfully promise a courtyard-to-edge margin.
        "placement": {"courtyard": {"sides": ["front", "back"]}},
        "routing": {
            "min_segment_mm": 0.1,
            "short_segment_justification": {"allow_pad_or_via_entry": True},
            "hygiene": {"forbid_duplicate_geometry": True,
                        "forbid_net_crossings": True,
                        "forbid_dangling": True},
            "provenance": "generated/routing.json",
            "search": routing_search(),
            "transforms": routing_transforms(),
        },
        "via_mask": {
            "pad_contact": {"populated_pad_attributes": ["SMD"],
                            "require_paste": True},
            "metric": "annulus_to_opening_mm",
            "note":
                "annulus_contacts counts zero-distance tangency as contact; "
                "annulus_strict_overlaps counts positive shared area only",
            "mask_dam_rule": "contact",
            "design_target_mm": 0.15,
            # The board's own 0.15 mm target is the tighter of the two and
            # is what the layout was drawn to. This names the fabricator's
            # published floor as well, so the vias are judged against the
            # process that will actually make them rather than against one
            # number this repository chose - and the same declaration turns
            # on the export check, which asks whether the Gerbers the
            # fabricator receives describe the same via the board does.
            "process": {
                "name": "JLCPCB PCB capabilities",
                "rule": "soldermask opening to neighbouring copper",
                "interpretation":
                    "a via annulus is copper that is not the opening's own "
                    "pad, so this published clearance is the process floor "
                    "for the annulus_to_opening_mm metric this board "
                    "already measures",
                "limit_from_catalog": {
                    "from_catalog": "soldermask_opening_to_trace_mm"},
            },
        },
        "catalog": {
            "normalized_sha256": physical.approved_snapshot()[
                "normalized_sha256"],
            "why":
                "the catalogue state fab/selection.json resolved this "
                "board's fabrication against, and the one fab/"
                "physical_inputs.json already cites for the finished "
                "copper; a limit cited from any other state would judge "
                "the board against rules it was never selected under",
        },
        "reference_continuity": reference_continuity(),
        "thermal": thermal.document(),
        "artifacts": {
            "gerber_dir": "generated/release/gerbers",
            "bom": "generated/release/bom.csv",
            "cpl": "generated/release/cpl.csv",
            "fabrication_manifest": "generated/release/fabrication.json",
            "validation_report": "generated/release/validation.json",
            "position_tolerance_mm": 0.01,
            "cpl_fields": {"designator": "Ref", "x": "PosX", "y": "PosY",
                           "side": "Side", "rotation": "Rot"},
            "cpl_origin": {"frame": "absolute page origin",
                           "offset_mm": [0.0, 0.0]},
            "gerber_export_flags": [
                "--layers",
                "F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,"
                "Edge.Cuts",
                "--no-protel-ext", "--use-drill-file-origin",
                "--subtract-soldermask"],
            "reports_dir": "generated/release/reports",
        },
        "archive": {
            "zip": "generated/release/%s-fabrication.zip" % project,
            "allow": [
                {"file_function": "Copper,L1,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Copper,L2,Bot", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Soldermask,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Soldermask,Bot", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Legend,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Legend,Bot", "require_payload": False,
                 "min_count": 1},
                {"file_function": "Paste,Top", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Profile,NP", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Drill/plated", "require_payload": True,
                 "min_count": 1},
                {"file_function": "Drill/nonplated", "require_payload": True,
                 "min_count": 1},
                {"file_function": "JobFile", "require_payload": True,
                 "min_count": 1},
            ],
        },
        "assembly": dict(
            assembly.document(),
            schematic_fields=["LCSC", "MPN", "Manufacturer"],
            required_part_fields=["LCSC"],
            bom_fields={"designators": "Designator", "value": "Comment",
                        "footprint": "Footprint", "quantity": "Quantity",
                        "LCSC": "LCSC Part #"},
            schematic_export={
                "fields": ["Reference", "Value", "Footprint", "${DNP}",
                           "${EXCLUDE_FROM_BOM}", "LCSC", "MPN",
                           "Manufacturer"],
                "labels": ["Reference", "Value", "Footprint", "DNP",
                           "ExcludeFromBOM", "LCSC", "MPN", "Manufacturer"],
                "flags": [],
                "reference_label": "Reference",
                "value_label": "Value",
                "footprint_label": "Footprint",
                "dnp_label": "DNP",
                "exclude_label": "ExcludeFromBOM",
                "true_tokens": ["1", "true", "yes", "x", "dnp"],
            },
            compared_part_fields=["LCSC", "MPN", "Manufacturer"],
        ),
        "release_generation": {
            "lock_file_globs": ["*.lck", "~*.lck", ".#*", "*-lock",
                                "*.kicad_prl-lock"],
            "erc": {"output": "erc.json"},
            "drc": {"output": "drc.json"},
            "drill": {"flags": ["--format", "excellon",
                                "--excellon-separate-th", "--drill-origin",
                                "plot"]},
            "bom": {
                "output": "bom.csv",
                "fields": ["${QUANTITY}", "Reference", "Value", "Footprint",
                           "LCSC"],
                "labels": ["Quantity", "Designator", "Comment", "Footprint",
                           "LCSC Part #"],
                "group_by": ["Value", "Footprint", "LCSC"],
                "flags": ["--exclude-dnp", "--ref-range-delimiter", ""],
                "field_map": {"designators": "Designator", "value": "Comment",
                              "footprint": "Footprint",
                              "quantity": "Quantity",
                              "LCSC": "LCSC Part #"},
            },
            "cpl": {
                "output": "cpl.csv",
                "flags": ["--format", "csv", "--units", "mm", "--side",
                          "both", "--exclude-dnp"],
                "field_map": {"designator": "Ref", "x": "PosX", "y": "PosY",
                              "side": "Side", "rotation": "Rot"},
                "origin": {"frame": "absolute page origin",
                           "offset_mm": [0.0, 0.0]},
            },
            "archive": {"zip": "%s-fabrication.zip" % project},
        },
        "reports": {
            "files": ["generated/release/reports/erc.json",
                      "generated/release/reports/drc.json"],
            "source_field": "source",
            "date_field": "date",
            "require_source_hash": True,
            "source_closure": ["*.kicad_sch", "*.kicad_pcb", "*.kicad_pro",
                               "*.kicad_dru", "constraints/*.json",
                               "sim/*.json", "fab/*.json",
                               "components/*.json", "evidence/index.json"],
            "source_hash_field": "source_sha256",
            "closure_field": "source_closure_sha256",
        },
        "fixture": {"attributes_file": ".gitattributes"},
        "release_profile": {
            "id": RELEASE_PROFILE_ID,
            "mandatory_gates": list(MANDATORY_GATES),
            "required_evidence": list(REQUIRED_EVIDENCE),
        },
        "simulation": {
            "stages": simulation_stages(),
            "required_stages": ["pre_layout", "post_layout"],
            "extracted_models": extracted_models(),
        },
        "connector_gender_tokens": {
            "receptacle": ["receptacle", "socket", "female"],
            "plug": ["plug", "header", "male"],
        },
        "connector_contracts": connector_contracts(),
    }


def document():
    from . import governance
    return governance.merged(_base_document())


def write():
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return MANIFEST_PATH


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
