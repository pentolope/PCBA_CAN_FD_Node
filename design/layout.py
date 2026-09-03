"""The board: outline, placement, pours and silkscreen, from the design source.

Board coordinates run x right and y UP from the lower-left corner, which is
the frame every dimension in this module is stated in. KiCad's own y runs
down, so the mapping is applied once, here.

The arrangement follows the two things that must not be compromised. The bus
enters at the bottom right and meets its protection, then its termination,
then the transceiver, in that order and in a straight line, over ground that
nothing is allowed to cut. Everything the field carries enters at the two
edges: the supply and the bus along the bottom, the field inputs and outputs
along the top, so no field conductor crosses the controller. The controller
sits between them, and the power chain runs along the bottom-left from the
supply terminal to the two logic rails.
"""
from __future__ import annotations

import json
import math
import os
import sys

from . import ksym, netlist

_TOOLKIT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tooling", "PCBA_AutoDesignAndTest")
if _TOOLKIT not in sys.path:
    sys.path.insert(0, _TOOLKIT)

from pcbqa import headless  # noqa: E402

headless.suppress_blocking_ui()

import pcbnew  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_PATH = os.path.join(REPO_ROOT, netlist.PROJECT_NAME + ".kicad_pcb")
PLACEMENT_PATH = os.path.join(REPO_ROOT, "constraints", "placement.json")

FOOTPRINT_SEARCH_PATHS = (
    os.path.join(REPO_ROOT, "library"),
    "/usr/share/kicad/footprints",
)

ORIGIN_MM = (30.0, 110.0)

BOARD_W_MM = 84.0
BOARD_H_MM = 66.0

EDGE_WIDTH_MM = 0.1
TRACK_WIDTH_MM = 0.25
#: Width of the generated field-supply and field-output conductors. Sized for
#: one channel's rating and, on the supply, for all four at once.
POWER_TRACK_WIDTH_MM = 0.6
FIELD_TRACK_WIDTH_MM = 1.0
#: Width of the generated bus pair, and the gap between the two conductors.
#: The pair is drawn rather than searched: constant spacing over unbroken
#: ground is a requirement, and a search has no freedom left inside it.
BUS_TRACK_WIDTH_MM = 0.3
BUS_GAP_MM = 0.3
CLEARANCE_MM = 0.15
EDGE_CLEARANCE_MM = 0.3
VIA_DIAMETER_MM = 0.6
VIA_DRILL_MM = 0.3
ZONE_INSET_MM = 0.5
STITCH_TRACK_WIDTH_MM = 0.4
#: How far a stitch's own annulus stands off the pad it bonds to. It is a
#: mask-opening figure, not a copper one: a via whose annulus touches the
#: opening of a pad that receives paste is a place for solder to wick away
#: down the barrel, and the board's own via-to-mask target is what this
#: keeps.
STITCH_GAP_MM = 0.45
#: The board's own via-to-mask-opening target, which a generated via is
#: held to as well as a routed one.
VIA_MASK_TARGET_MM = 0.15

#: Field terminal blocks sit with their wire entry on the board edge; the pin
#: row stands this far inside it.
TERMINAL_PIN_INSET_MM = 5.5
TERMINAL_PITCH_MM = 5.08

#: Where each connector's pin row sits.
BOTTOM_ROW_Y_MM = TERMINAL_PIN_INSET_MM
TOP_ROW_Y_MM = BOARD_H_MM - TERMINAL_PIN_INSET_MM

#: The one lane between the crystal and the controller. The field supply
#: runs up it, which is the only way it reaches the output connector's
#: supply contact without crossing a channel.
FIELD_CORRIDOR_X_MM = 32.4

SUPPLY_TERMINAL_X_MM = 12.0
BUS_TERMINAL_X_MM = 60.0
OUTPUT_TERMINAL_X_MM = 20.0
INPUT_TERMINAL_X_MM = 56.0

#: The bus corridor: the pair runs straight up this line from the connector,
#: through the protection and the termination tap, to the transceiver. The
#: corridor is the midpoint of the connector's own two bus contacts, so the
#: fan-in from the terminal block's 5.08 pitch is symmetric.
BUS_CORRIDOR_X_MM = BUS_TERMINAL_X_MM + TERMINAL_PITCH_MM / 2.0
#: Separation of the two conductors, which is the transceiver's own pad
#: separation: the pair arrives at the pads it is drawn for and nothing has
#: to fan out at the end of the run.
BUS_PAIR_SEPARATION_MM = 1.27
BUS_PROTECTOR_Y_MM = 14.0
BUS_TERMINATION_Y_MM = 19.0
BUS_LINK_X_OFFSET_MM = 11.5
BUS_TRANSCEIVER_Y_MM = 29.0
#: The centre of the split termination carries no differential current, so
#: it is the one conductor that may take the long way round: it runs along
#: the bottom of the board, below the connector's contacts, where it crosses
#: neither bus conductor.
BUS_SPLIT_RETURN_Y_MM = 2.2

#: The back-layer copper under the pair, between one station and the next.
#: Nothing may cut it, so the stretches between the parts are rule areas
#: rather than a hope. The stations themselves are left out, and so is the
#: stretch immediately below the protector: that is where the protector's
#: own reference via goes, and a via on the reference net ties the pour
#: together rather than cutting it - which is the whole point of the short
#: return path the brief asks for there.
BUS_KEEPOUT_HALF_WIDTH_MM = 1.6
BUS_KEEPOUT_SPANS_MM = ((8.0, 11.2), (15.7, 17.6), (20.4, 22.4),
                        (24.6, BUS_TRANSCEIVER_Y_MM - 3.2))

#: Rows inside a field-output column, from the connector down.
OUTPUT_ROWS_MM = {"clamp": 50.5, "switch": 46.0, "gate": 42.0,
                  "series": 38.5}
#: Rows inside a field-input column, from the connector down.
INPUT_ROWS_MM = {"upper": 50.5, "lower": 47.1, "clamp": 43.7,
                 "filter": 40.3, "series": 36.9}
#: How far a channel's clamp stands off its own lane. The clamp's other
#: terminal is the reference, and it belongs beside the lane rather than in
#: it: the conductor that carries the channel's current runs straight up the
#: lane through the clamp's first pad and reaches the contact without
#: stepping round anything.
OUTPUT_CLAMP_OFFSET_MM = 1.60
INPUT_CLAMP_OFFSET_MM = -1.65

MOUNTING_HOLES_MM = {
    "H1": (3.5, 3.5),
    "H2": (BOARD_W_MM - 3.5, 3.5),
    "H3": (3.5, BOARD_H_MM - 3.5),
    "H4": (BOARD_W_MM - 3.5, BOARD_H_MM - 3.5),
}

#: Parts a placement search may not move, and why.
#:
#: The connectors and the fasteners are the board's mechanical contract. The
#: test points are its service contract. The bus protector, the termination
#: and the transceiver are the one chain whose order the brief fixes, and the
#: pair between them is generated copper, so their positions are the topology
#: rather than an input to it.
LOCKED_REFERENCES = tuple(sorted(
    [reference for reference in netlist.PARTS
     if reference[0] in ("J", "H") and reference[1:].isdigit()]
    + [reference for reference in netlist.PARTS
       if reference.startswith("TP")]
    + ["U2", "D4", "R9", "R10", "C20"]))


def connector_pin_x(reference, pin):
    """Where one contact of a bottom- or top-edge terminal block sits.

    The top-edge blocks face outward, so they are turned round and their
    contacts run right to left. A channel column stands under its own
    contact, so the column positions are read from here rather than declared
    a second time and left to drift.
    """
    centre, _y, rotation = SHARED_PLACEMENT[reference]
    count = len(netlist.CONNECTOR_PIN_ORDER[reference])
    span = TERMINAL_PITCH_MM * (count - 1) / 2.0
    offset = -span + TERMINAL_PITCH_MM * (pin - 1)
    return centre + (offset if rotation == 0.0 else -offset)


def _output_lane_x(channel):
    return connector_pin_x("J3", channel + 1)


def _input_lane_x(channel):
    return connector_pin_x("J4", channel + 1)


def _output_seed(channel):
    """One field-output column: clamp, switch, then the gate network.

    Every part stands in the 5.08 lane its own contact occupies, so a
    channel's current never crosses another channel's.
    """
    x = _output_lane_x(channel)
    rows = OUTPUT_ROWS_MM
    return {
        "D%d" % (channel + 8): (x + OUTPUT_CLAMP_OFFSET_MM, rows["clamp"],
                                0.0),
        "Q%d" % (channel + 1): (x, rows["switch"], 90.0),
        "R%d" % (channel + 29): (x, rows["gate"], 90.0),
        "R%d" % (channel + 25): (x, rows["series"], 90.0),
    }


def _input_seed(channel):
    """One field-input column: divider, clamp, filter and series element."""
    x = _input_lane_x(channel)
    rows = INPUT_ROWS_MM
    return {
        "R%d" % (channel + 13): (x, rows["upper"], 90.0),
        "R%d" % (channel + 17): (x, rows["lower"], 90.0),
        "D%d" % (channel + 4): (x + INPUT_CLAMP_OFFSET_MM, rows["clamp"],
                                0.0),
        "C%d" % (channel + 20): (x, rows["filter"], 90.0),
        "R%d" % (channel + 21): (x, rows["series"], 90.0),
    }


#: Everything that is not part of a field channel, left to right and bottom
#: to top: the supply terminal and its protection, the converter and its
#: regulator, the controller and its crystal, and the bus chain.
SHARED_PLACEMENT = {
    # the supply terminal, its clamp and the reverse-blocking device, which
    # sits in the return so the bus connector's reference pin can be the
    # board's own
    "J1": (13.0, BOTTOM_ROW_Y_MM, 0.0),
    "D1": (23.0, BOTTOM_ROW_Y_MM, 0.0),
    "Q1": (20.5, 13.0, 0.0),
    "R1": (17.0, 16.5, 0.0),
    "D2": (22.0, 16.5, 0.0),
    "C1": (11.5, 18.5, 0.0),
    "C2": (19.0, 21.0, 0.0),
    "TP1": (4.5, 10.0, 0.0),
    # the step-down converter. Its order along the board is the order of the
    # switching loop: the input capacitors, the converter, the catch diode,
    # the inductor, the output capacitors. The loop that carries the
    # switched current is the input capacitors, the converter's input and
    # switch pins, the diode and the reference, and it is that loop, not the
    # schematic, that decides these positions: the diode stands one
    # footprint from the converter and directly above the input capacitors,
    # so the loop encloses a few square millimetres of the reference plane
    # beneath it rather than the width of the board.
    "C4": (30.0, 4.8, 0.0),
    "C5": (35.5, 4.8, 0.0),
    "U3": (30.0, 11.4, 0.0),
    "R4": (25.0, 11.0, 0.0),
    "R5": (25.0, 14.0, 0.0),
    "D3": (36.0, 9.0, 0.0),
    "L1": (43.5, 12.35, 0.0),
    "C3": (33.0, 15.0, 0.0),
    # the feedback divider stands away from the switch node and the
    # bootstrap capacitor, on the quiet side of the converter, so the node
    # the converter regulates on runs beside neither of them. What is long
    # is instead the sense conductor from the output, which is a rail.
    "R2": (27.0, 8.6, 180.0),
    "R3": (23.5, 8.6, 0.0),
    # the output capacitors stay clear of the lane the termination's centre
    # node comes down in, which owns the column outboard of the links
    "C6": (43.0, 5.2, 0.0),
    "C7": (43.0, 8.2, 0.0),
    "C8": (43.5, 17.0, 0.0),
    "TP3": (39.8, 17.6, 0.0),
    # the logic regulator and the indicator
    "U4": (44.0, 22.5, 0.0),
    "C9": (48.5, 22.5, 0.0),
    "C10": (48.5, 25.5, 0.0),
    "R6": (44.0, 26.0, 0.0),
    "TP4": (24.0, 30.5, 0.0),
    "TP5": (24.0, 26.5, 0.0),
    "R11": (20.0, 24.5, 0.0),
    "D13": (24.5, 24.5, 0.0),
    # the controller, its crystal and its debug port
    "U1": (38.5, 34.0, 0.0),
    "C11": (36.0, 42.5, 0.0),
    "C12": (45.5, 31.0, 0.0),
    "C13": (37.0, 27.5, 0.0),
    "C14": (41.0, 27.5, 0.0),
    "C15": (35.0, 40.0, 0.0),
    "Y1": (28.5, 33.0, 0.0),
    "C16": (28.5, 37.0, 0.0),
    "C17": (28.5, 29.0, 0.0),
    "R7": (40.0, 42.5, 90.0),
    "R12": (52.0, 33.0, 0.0),
    "R13": (52.0, 30.0, 0.0),
    "J5": (78.0, 40.0, 0.0),
    # the bus: connector, protection, termination, transceiver, in that
    # order up one corridor. The protector's reference pad faces the
    # connector, so the discharge it diverts returns to the contact it came
    # from over the shortest path the geometry allows.
    "J2": (BUS_TERMINAL_X_MM, BOTTOM_ROW_Y_MM, 0.0),
    "D4": (BUS_CORRIDOR_X_MM, BUS_PROTECTOR_Y_MM, 270.0),
    "R10": (BUS_CORRIDOR_X_MM - 5.4, BUS_TERMINATION_Y_MM, 180.0),
    "R9": (BUS_CORRIDOR_X_MM + 5.4, BUS_TERMINATION_Y_MM, 0.0),
    "J7": (BUS_CORRIDOR_X_MM - BUS_LINK_X_OFFSET_MM,
           BUS_TERMINATION_Y_MM, 270.0),
    "J6": (BUS_CORRIDOR_X_MM + BUS_LINK_X_OFFSET_MM,
           BUS_TERMINATION_Y_MM, 90.0),
    "TP7": (BUS_CORRIDOR_X_MM - 6.5, 23.5, 0.0),
    "TP6": (BUS_CORRIDOR_X_MM + 6.5, 23.5, 0.0),
    "C20": (BUS_CORRIDOR_X_MM + BUS_LINK_X_OFFSET_MM + 2.54, 23.5, 90.0),
    "U2": (BUS_CORRIDOR_X_MM, BUS_TRANSCEIVER_Y_MM, 270.0),
    "C18": (BUS_CORRIDOR_X_MM - 3.5, BUS_TRANSCEIVER_Y_MM + 5.0, 0.0),
    "C19": (BUS_CORRIDOR_X_MM + 3.5, BUS_TRANSCEIVER_Y_MM + 5.0, 0.0),
    "R8": (BUS_CORRIDOR_X_MM + 6.0, BUS_TRANSCEIVER_Y_MM, 0.0),
    "TP8": (55.0, 33.0, 0.0),
    "TP9": (55.0, 29.5, 0.0),
    # the field connectors and the field supply path. The supply contact is
    # the one at the turned-round block's right-hand end, so the fuse that
    # feeds it stands to the right of the output columns and its conductor
    # crosses no channel.
    "J3": (OUTPUT_TERMINAL_X_MM, TOP_ROW_Y_MM, 180.0),
    "J4": (INPUT_TERMINAL_X_MM, TOP_ROW_Y_MM, 180.0),
    "F1": (36.5, 19.5, 90.0),
    "TP2": (FIELD_CORRIDOR_X_MM, 27.0, 0.0),
}


def to_board(x_mm, y_mm):
    return (ORIGIN_MM[0] + x_mm, ORIGIN_MM[1] - y_mm)


def _point(x_mm, y_mm):
    bx, by = to_board(x_mm, y_mm)
    return pcbnew.VECTOR2I(pcbnew.FromMM(bx), pcbnew.FromMM(by))


def accepted_placement():
    """The placement a search accepted, if one has been recorded.

    Absent, the seed below is the placement. Present, it replaces the seed
    for every part that is not locked - a locked part is locked in the board
    file and the search cannot have moved it, so accepting one from this file
    would be accepting a value that never came from a search.
    """
    if not os.path.isfile(PLACEMENT_PATH):
        return {}
    with open(PLACEMENT_PATH, encoding="utf-8") as handle:
        document = json.load(handle)
    return {reference: tuple(pose)
            for reference, pose in document["placement"].items()
            if reference not in LOCKED_REFERENCES}


def seed_placement():
    placed = dict(SHARED_PLACEMENT)
    for reference, (x, y) in MOUNTING_HOLES_MM.items():
        placed[reference] = (x, y, 0.0)
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        placed.update(_output_seed(channel))
    for channel in range(1, netlist.INPUT_COUNT + 1):
        placed.update(_input_seed(channel))
    return placed


def fixed_placements():
    placed = seed_placement()
    for reference, pose in accepted_placement().items():
        if reference not in placed:
            raise KeyError("accepted placement names an unknown part: "
                           + reference)
        placed[reference] = pose
    missing = sorted(reference for reference, part in netlist.PARTS.items()
                     if part["footprint"] and reference not in placed)
    if missing:
        raise KeyError("no placement for " + ", ".join(missing))
    return placed


def _footprint_dir(footprint):
    library, _, name = footprint.partition(":")
    for base in FOOTPRINT_SEARCH_PATHS:
        candidate = os.path.join(base, library + ".pretty")
        if os.path.isfile(os.path.join(candidate, name + ".kicad_mod")):
            return candidate, name
    raise FileNotFoundError(footprint)


_PIN_NAMES = {}


def _pin_name(lib_id, number):
    if lib_id not in _PIN_NAMES:
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        _PIN_NAMES[lib_id] = {
            key: pins[0].name for key, pins in library.pins(lib_id).items()}
    return _PIN_NAMES[lib_id].get(number, "")


def _floating_net(board, reference, number):
    lib_id = netlist.PARTS[reference]["lib_id"]
    name = "unconnected-(%s-%s-Pad%s)" % (
        reference, _pin_name(lib_id, number).replace("/", "{slash}"), number)
    existing = board.GetNetInfo().GetNetItem(name)
    if existing is not None and existing.GetNetCode() != 0:
        return existing
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def _load(board, reference, part, x, y, rotation, pin_net, nets):
    library_dir, name = _footprint_dir(part["footprint"])
    footprint = pcbnew.FootprintLoad(library_dir, name)
    if footprint is None:
        raise RuntimeError("could not load " + part["footprint"])
    library = part["footprint"].partition(":")[0]
    footprint.SetFPID(pcbnew.LIB_ID(library, name))
    footprint.SetPosition(_point(x, y))
    footprint.SetOrientationDegrees(rotation)
    footprint.SetReference(reference)
    footprint.SetValue(part["value"])
    footprint.Reference().SetLayer(pcbnew.F_Fab)
    footprint.Value().SetLayer(pcbnew.F_Fab)
    for key, value in (("MPN", part["mpn"]), ("LCSC", part["lcsc"]),
                       ("Manufacturer", part["manufacturer"])):
        if not value:
            continue
        footprint.SetField(key, value)
        for field in footprint.GetFields():
            if field.GetName() == key:
                field.SetLayer(pcbnew.F_Fab)
                field.SetVisible(False)
    if not part["in_bom"]:
        footprint.SetExcludedFromBOM(True)
    if reference in LOCKED_REFERENCES:
        footprint.SetLocked(True)
    for pad in footprint.Pads():
        number = pad.GetNumber()
        if not number:
            continue
        net_name = pin_net.get("%s.%s" % (reference, number))
        if net_name:
            pad.SetNet(nets[net_name])
        else:
            pad.SetNet(_floating_net(board, reference, number))
    board.Add(footprint)
    return footprint


def _nets(board):
    created = {}
    for name in sorted(netlist.NETS):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        created[name] = net
    return created


def _design_settings(board):
    board.SetCopperLayerCount(2)
    settings = board.GetDesignSettings()
    settings.m_TrackMinWidth = pcbnew.FromMM(0.15)
    settings.m_ViasMinSize = pcbnew.FromMM(0.45)
    settings.m_MinThroughDrill = pcbnew.FromMM(0.25)
    settings.m_CopperEdgeClearance = pcbnew.FromMM(EDGE_CLEARANCE_MM)
    settings.m_HoleClearance = pcbnew.FromMM(0.25)
    settings.m_HoleToHoleMin = pcbnew.FromMM(0.25)
    settings.m_ViasMinAnnularWidth = pcbnew.FromMM(0.1)
    settings.m_MinClearance = pcbnew.FromMM(CLEARANCE_MM)
    default_class = settings.m_NetSettings.GetDefaultNetclass()
    default_class.SetClearance(pcbnew.FromMM(CLEARANCE_MM))
    default_class.SetTrackWidth(pcbnew.FromMM(TRACK_WIDTH_MM))
    default_class.SetViaDiameter(pcbnew.FromMM(VIA_DIAMETER_MM))
    default_class.SetViaDrill(pcbnew.FromMM(VIA_DRILL_MM))


def _add_outline(board):
    corners = [(0.0, 0.0), (BOARD_W_MM, 0.0), (BOARD_W_MM, BOARD_H_MM),
               (0.0, BOARD_H_MM)]
    closed = corners + [corners[0]]
    for start, end in zip(closed, closed[1:]):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(_point(*start))
        shape.SetEnd(_point(*end))
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(pcbnew.FromMM(EDGE_WIDTH_MM))
        board.Add(shape)


def _rectangle_zone(board, corners, layers):
    zone = pcbnew.ZONE(board)
    layer_set = pcbnew.LSET()
    for layer in layers:
        layer_set.addLayer(layer)
    zone.SetLayerSet(layer_set)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in corners:
        bx, by = to_board(x, y)
        outline.Append(pcbnew.FromMM(bx), pcbnew.FromMM(by))
    return zone


def _pour(board, net, corners, layers, priority=0):
    zone = _rectangle_zone(board, corners, layers)
    zone.SetNet(net)
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(pcbnew.FromMM(CLEARANCE_MM))
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    board.Add(zone)
    return zone


def _keepout(board, corners, layers):
    """A rule area no track or via may enter.

    The bus pair's return path is a requirement, not a preference: a router
    that put one track across the ground under the pair would break it, and
    a board cannot be inspected afterwards for a hole that is only visible
    if you know to look. So the region is declared here and the design rule
    check enforces it.
    """
    zone = _rectangle_zone(board, corners, layers)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowZoneFills(False)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    board.Add(zone)
    return zone


def ground_outline():
    """The reference pour: the whole back layer, inset from the edge."""
    inset = ZONE_INSET_MM
    return [(inset, inset), (BOARD_W_MM - inset, inset),
            (BOARD_W_MM - inset, BOARD_H_MM - inset),
            (inset, BOARD_H_MM - inset)]


#: The protected input rail as one pour on the front layer, over the corner
#: the supply terminal, its clamp and its reservoir sit in and along the
#: converter row that ends at the resettable fuse. An L rather than a
#: rectangle because the rail's own parts stand in one, and a rectangle that
#: covered both arms would cover the controller as well.
INPUT_POUR_OUTLINE_MM = ((3.0, 3.0), (38.5, 3.0), (38.5, 21.0),
                         (25.0, 21.0), (25.0, 22.5), (3.0, 22.5))


def _add_pours(board, nets):
    _pour(board, nets[netlist.GROUND_NET], ground_outline(), (pcbnew.B_Cu,))
    _pour(board, nets[netlist.INPUT_RAIL_NET],
          list(INPUT_POUR_OUTLINE_MM), (pcbnew.F_Cu,), priority=1)
    for y0, y1 in BUS_KEEPOUT_SPANS_MM:
        x0 = BUS_CORRIDOR_X_MM - BUS_KEEPOUT_HALF_WIDTH_MM
        x1 = BUS_CORRIDOR_X_MM + BUS_KEEPOUT_HALF_WIDTH_MM
        _keepout(board, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                 (pcbnew.B_Cu,))


#: Copper drawn for its geometry is locked. The pair's spacing, the loop the
#: converter switches into, the one conductor a channel's current has: each
#: is drawn because that shape is the requirement, and a search that
#: reroutes it has removed the requirement without anyone noticing. The
#: router treats a net carrying locked copper as one it may not rip, which
#: is exactly the statement being made.
#:
#: The reference's stitching is the exception, and is added unlocked. A
#: stitch says only that this pad reaches the plane; which via it reaches it
#: through is not a requirement, and holding every one of them still leaves
#: the search no way to keep the plane in one piece when it has to cross the
#: back layer. What the stitching has to achieve is checked afterwards, on
#: the routed board, by the same connectivity check everything else is.
def _add_track(board, start, end, layer, net, width_mm, locked=True):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start)
    track.SetEnd(end)
    track.SetLayer(layer)
    track.SetNet(net)
    track.SetWidth(pcbnew.FromMM(width_mm))
    track.SetLocked(locked)
    board.Add(track)
    return track


def _add_via(board, position, net, locked=True):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(position)
    via.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(VIA_DIAMETER_MM))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL_MM))
    via.SetNet(net)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetLocked(locked)
    board.Add(via)
    return via


def _pad(footprints, reference, number):
    for pad in footprints[reference].Pads():
        if pad.GetNumber() == number:
            return pad
    raise KeyError("%s has no pad %s" % (reference, number))


def _inside_bus_keepout(x_mm, y_mm, margin):
    """Whether a via at this point would land in a protected stretch."""
    half = BUS_KEEPOUT_HALF_WIDTH_MM + margin
    if abs(x_mm - BUS_CORRIDOR_X_MM) > half:
        return False
    return any(y0 - margin <= y_mm <= y1 + margin
               for y0, y1 in BUS_KEEPOUT_SPANS_MM)


def _obstacles(board):
    """Everything a stitch has to keep away from, and the net each belongs to.

    A pad is a box, because an LQFP land is five times longer than it is
    wide and a circle round it either swallows its neighbours or misses the
    land. A track is a segment, because the box round a diagonal one covers
    a region the copper never touches. The one thing a stitch may approach
    is copper on its own net.
    """
    found = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            box = pad.GetBoundingBox()
            found.append(("box", box.GetLeft(), box.GetTop(), box.GetRight(),
                          box.GetBottom(), 0.0, pad.GetNetCode()))
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            position = item.GetPosition()
            found.append(("seg", position.x, position.y, position.x,
                          position.y, item.GetWidth(pcbnew.F_Cu) / 2.0,
                          item.GetNetCode()))
            continue
        start, end = item.GetStart(), item.GetEnd()
        found.append(("seg", start.x, start.y, end.x, end.y,
                      item.GetWidth() / 2.0, item.GetNetCode()))
    return found


def _obstacle_distance(x, y, obstacle):
    kind = obstacle[0]
    if kind == "box":
        left, top, right, bottom = obstacle[1:5]
        dx = max(left - x, 0.0, x - right)
        dy = max(top - y, 0.0, y - bottom)
        return math.hypot(dx, dy)
    x1, y1, x2, y2, half = obstacle[1:6]
    length_squared = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if length_squared == 0:
        return max(0.0, math.hypot(x - x1, y - y1) - half)
    t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / length_squared
    t = min(1.0, max(0.0, t))
    return max(0.0, math.hypot(x - (x1 + t * (x2 - x1)),
                               y - (y1 + t * (y2 - y1))) - half)


def _clear_of(obstacles, net_code, points, reach, pad_reach=None,
              same_net_pads_count=False):
    """Whether every sampled point keeps its distance from what is there.

    Pads may take their own figure. For a via that figure applies whatever
    net the pad is on: what a via has to clear at a pad is not its copper
    but its solder-mask opening, and solder wicks down a barrel beside a pad
    of its own net just as readily as beside any other. For the copper that
    reaches the via, same-net pads are ignored, which is what lets a stitch
    leave the pad it bonds to.
    """
    if pad_reach is None:
        pad_reach = reach
    for x, y in points:
        for obstacle in obstacles:
            is_pad = obstacle[0] == "box"
            if obstacle[6] == net_code and not (is_pad
                                                and same_net_pads_count):
                continue
            needed = pad_reach if is_pad else reach
            if _obstacle_distance(x, y, obstacle) < needed:
                return False
    return True


def _stitch(board, footprint, pad, net):
    """Drop a via just outside a surface pad and bond it to its pour.

    The direction is searched rather than assumed: on a board where a
    passive row steps by little more than its own courtyard, the obvious
    direction is often occupied, and a via that lands on a neighbour's mask
    opening is a bridge, not a connection. What is checked is not only the
    via but the copper that reaches it, because a stitch that clears every
    pad and then crosses a track on the way is still a short.
    """
    position = pad.GetPosition()
    size = pad.GetSize()
    angle = math.radians(footprint.GetOrientationDegrees())
    along = (math.cos(angle), math.sin(angle))
    across = (-math.sin(angle), math.cos(angle))
    half_along = pcbnew.ToMM(size.x) / 2.0
    half_across = pcbnew.ToMM(size.y) / 2.0
    obstacles = _obstacles(board)
    net_code = net.GetNetCode()
    via_reach = pcbnew.FromMM(VIA_DIAMETER_MM / 2.0 + CLEARANCE_MM)
    via_pad_reach = pcbnew.FromMM(VIA_DIAMETER_MM / 2.0 + VIA_MASK_TARGET_MM
                                  + 0.05)
    track_reach = pcbnew.FromMM(STITCH_TRACK_WIDTH_MM / 2.0 + CLEARANCE_MM)
    # the two pad axes first, because a stitch that leaves along one of them
    # is the shortest and the one a reader expects; then every other
    # direction, because on a dense row the expected one is often occupied
    candidates = []
    base = max(half_along, half_across) + VIA_DIAMETER_MM / 2.0 + STITCH_GAP_MM
    radii = [base + extra for extra in (0.0, 0.3, 0.6, 0.9, 1.2, 1.8,
                                       2.4, 3.0)]
    for radius in radii:
        for axis in (across, along):
            for sign in (1.0, -1.0):
                candidates.append((axis[0] * sign * radius,
                                   axis[1] * sign * radius))
        for step in range(16):
            theta = angle + step * math.pi / 8.0
            candidates.append((math.cos(theta) * radius,
                               math.sin(theta) * radius))
    for dx, dy in candidates:
        centre = pcbnew.VECTOR2I(int(position.x + pcbnew.FromMM(dx)),
                                 int(position.y + pcbnew.FromMM(dy)))
        x_mm = pcbnew.ToMM(centre.x) - ORIGIN_MM[0]
        y_mm = ORIGIN_MM[1] - pcbnew.ToMM(centre.y)
        margin = VIA_DIAMETER_MM / 2.0 + CLEARANCE_MM
        if _inside_bus_keepout(x_mm, y_mm, margin):
            continue
        if not (ZONE_INSET_MM + margin <= x_mm
                <= BOARD_W_MM - ZONE_INSET_MM - margin
                and ZONE_INSET_MM + margin <= y_mm
                <= BOARD_H_MM - ZONE_INSET_MM - margin):
            continue
        if not _clear_of(obstacles, net_code, [(centre.x, centre.y)],
                         via_reach, via_pad_reach,
                         same_net_pads_count=True):
            continue
        # sample the copper that reaches the via, from the edge of the pad
        # it starts on outward: inside that pad there is nothing to clear
        span = math.hypot(centre.x - position.x, centre.y - position.y)
        start = min(1.0, pcbnew.FromMM(max(half_along, half_across)) / span)
        steps = max(1, int(span / pcbnew.FromMM(0.2)))
        samples = []
        for index in range(steps + 1):
            fraction = start + (1.0 - start) * index / float(steps)
            samples.append((position.x + (centre.x - position.x) * fraction,
                            position.y + (centre.y - position.y) * fraction))
        if not _clear_of(obstacles, net_code, samples, track_reach):
            continue
        _add_via(board, centre, net, locked=False)
        _add_track(board, position, centre, pcbnew.F_Cu, net,
                   STITCH_TRACK_WIDTH_MM, locked=False)
        return centre
    raise RuntimeError(
        "no clear stitch position for %s pad %s"
        % (footprint.GetReference(), pad.GetNumber()))


def _stitch_grounds(board, footprints, nets):
    """Every surface pad on the reference reaches the pour through its own via.

    The reference is a pour on the back layer, so a pad that exists only on
    the front is not on it until something takes it there. Doing it here
    rather than leaving it to the router keeps the reference connection a
    property of the pad's net, not of a search.
    """
    for reference, footprint in sorted(footprints.items()):
        for pad in footprint.Pads():
            if pad.GetNetname() != netlist.GROUND_NET:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            _stitch(board, footprint, pad, nets[netlist.GROUND_NET])


# ---------------------------------------------------------------------------
# generated copper

#: Where the fan from the connector's own 5.08 pitch ends and the pair
#: proper begins.
BUS_FAN_Y_MM = BOTTOM_ROW_Y_MM + 2.5


def _route_bus_pair(board, footprints, nets):
    """The two bus conductors, as one coupled pair from end to end.

    From each contact the conductor rises, converges once onto its lane, and
    then runs straight up the corridor at the separation the protector and
    the transceiver both present, through the protector's own pads, past the
    termination tap, to the transceiver. The brief asks for constant spacing
    over an unbroken return with no stubs, and that is a topology, not a
    search result. What leaves the pair - one termination leg and one probe
    on each side - leaves outward, away from the other conductor, so neither
    tap passes over the one it does not belong to.
    """
    for net_name, sign, protector_pad, transceiver_pad, connector_pad, \
            leg_reference, probe_reference in (
            ("CANH", +1.0, "1", "7", "3", "R9", "TP6"),
            ("CANL", -1.0, "2", "6", "2", "R10", "TP7")):
        net = nets[net_name]
        connector = _pad(footprints, "J2", connector_pad).GetPosition()
        protector = _pad(footprints, "D4", protector_pad).GetPosition()
        transceiver = _pad(footprints, "U2", transceiver_pad).GetPosition()
        lane_x = protector.x
        points = [connector, protector, transceiver]
        for first, second in zip(points, points[1:]):
            _add_track(board, first, second, pcbnew.F_Cu, net,
                       BUS_TRACK_WIDTH_MM)
        for reference, pad_number in ((leg_reference, "1"),
                                      (probe_reference, "1")):
            tap = _pad(footprints, reference, pad_number).GetPosition()
            junction = pcbnew.VECTOR2I(lane_x, tap.y)
            _add_track(board, junction, tap, pcbnew.F_Cu, net,
                       BUS_TRACK_WIDTH_MM)


def _route_termination_centre(board, footprints, nets):
    """The centre of the split termination, joined below the connector.

    The two legs sit on opposite sides of the pair, so their centre node has
    to get from one side to the other. It carries no differential current -
    it is the pair's own virtual ground - so it is the one conductor that
    may take the long way round, and it does: down the outside of each link,
    along the bottom of the board below the connector's contacts, where it
    crosses neither bus conductor.
    """
    net = nets["TERM_SPLIT"]
    left = _pad(footprints, "J7", "2").GetPosition()
    right = _pad(footprints, "J6", "2").GetPosition()
    centre = _pad(footprints, "C20", "1").GetPosition()
    bottom = _point(0.0, BUS_SPLIT_RETURN_Y_MM).y
    points = [left, pcbnew.VECTOR2I(left.x, bottom),
              pcbnew.VECTOR2I(right.x, bottom), right,
              pcbnew.VECTOR2I(right.x, centre.y), centre]
    for first, second in zip(points, points[1:]):
        _add_track(board, first, second, pcbnew.F_Cu, net, TRACK_WIDTH_MM)


#: The lane the two input capacitors are tied together in, below their own
#: row and inside the input rail's pour. It exists because the pour's shape
#: is a result of everything else on the front layer, and the loop these
#: capacitors close with the converter is a requirement.
CONVERTER_INPUT_LANE_Y_MM = 3.4


def _route_converter_input(board, footprints, nets):
    """The converter's input capacitors, tied to each other.

    Each capacitor sits on the input rail's pour, and the pour is what
    carries the rail to the converter's input pin a few millimetres away.
    What the pour cannot promise is that it stays one piece: it fills around
    whatever else the front layer ends up carrying, and a capacitor that
    ends up on an island of its own is a capacitor that is not in the loop.
    This is the conductor that says otherwise.
    """
    net = nets[netlist.INPUT_RAIL_NET]
    near = _pad(footprints, "C4", "1").GetPosition()
    far = _pad(footprints, "C5", "1").GetPosition()
    lane = _point(0.0, CONVERTER_INPUT_LANE_Y_MM).y
    points = [near, pcbnew.VECTOR2I(near.x, lane),
              pcbnew.VECTOR2I(far.x, lane), far]
    for first, second in zip(points, points[1:]):
        if first == second:
            continue
        _add_track(board, first, second, pcbnew.F_Cu, net,
                   POWER_TRACK_WIDTH_MM)


def _route_switch_node(board, footprints, nets):
    """The converter's switch node.

    This is the one conductor on the board whose voltage moves the whole
    input rail in a few nanoseconds, and the area it encloses with the catch
    diode and the input capacitors is what that edge radiates from. That
    area is a requirement, not something to be optimised for length, so the
    node is drawn: one run from the switch pin to the inductor, one branch
    down to the diode's cathode and one up to the bootstrap capacitor. Every
    piece is on the component side, because a via in this node would put the
    switched edge on the reference layer's other side.
    """
    net = nets["SW_NODE"]
    switch = _pad(footprints, "U3", "6").GetPosition()
    inductor = _pad(footprints, "L1", "1").GetPosition()
    diode = _pad(footprints, "D3", "1").GetPosition()
    boot = _pad(footprints, "C3", "2").GetPosition()
    runs = ((switch, inductor),
            (pcbnew.VECTOR2I(diode.x, switch.y), diode),
            (pcbnew.VECTOR2I(boot.x, switch.y), boot))
    for first, second in runs:
        if first == second:
            continue
        _add_track(board, first, second, pcbnew.F_Cu, net,
                   POWER_TRACK_WIDTH_MM)


#: The stretch of the field supply's lane that runs on the back layer.
#: The lane passes between the crystal and the controller, and the
#: oscillator's own two conductors have to cross it to reach the pins they
#: belong to. One of the two has to give way, and it is this one: a rail
#: carrying direct current is what a via costs nothing on, while an
#: oscillator's conductor pays for every via in reference it no longer has.
#: The span is wider than the crossing itself so the search has room to make
#: the crossing rather than exactly enough.
FIELD_CORRIDOR_BACK_SPAN_MM = (30.0, 41.5)


def _route_field_supply(board, footprints, nets):
    """The field supply, from the fuse to the contact it feeds.

    The whole of every channel's current runs through it, so it is drawn at
    a width chosen for that current rather than left to a search that
    optimises for length. It runs up the one lane between the crystal and
    the controller, and reaches the connector's supply contact from the side
    the channels are not on, so it crosses none of them. Its probe stands on
    the lane, which is why the conductor passes through the probe's pad
    rather than stopping at it. Beside the oscillator it changes layer, so
    the crystal's own conductors can reach their pins on the front without
    crossing this one.
    """
    net = nets[netlist.FIELD_SUPPLY_NET]
    start = _pad(footprints, "F1", "2").GetPosition()
    probe = _pad(footprints, "TP2", "1").GetPosition()
    end = _pad(footprints, "J3", "1").GetPosition()
    lane_x = _point(FIELD_CORRIDOR_X_MM, 0.0).x
    lower, upper = (_point(0.0, span).y
                    for span in FIELD_CORRIDOR_BACK_SPAN_MM)
    runs = ((pcbnew.F_Cu, start, pcbnew.VECTOR2I(lane_x, start.y)),
            (pcbnew.F_Cu, pcbnew.VECTOR2I(lane_x, start.y), probe),
            (pcbnew.F_Cu, probe, pcbnew.VECTOR2I(lane_x, lower)),
            (pcbnew.B_Cu, pcbnew.VECTOR2I(lane_x, lower),
             pcbnew.VECTOR2I(lane_x, upper)),
            (pcbnew.F_Cu, pcbnew.VECTOR2I(lane_x, upper),
             pcbnew.VECTOR2I(lane_x, end.y)),
            (pcbnew.F_Cu, pcbnew.VECTOR2I(lane_x, end.y), end))
    for layer, first, second in runs:
        if first == second:
            continue
        _add_track(board, first, second, layer, net, FIELD_TRACK_WIDTH_MM)
    for crossing in (lower, upper):
        _add_via(board, pcbnew.VECTOR2I(lane_x, crossing), net)


def _route_field_outputs(board, footprints, nets):
    """Each field output, from its switch to its own connector pin."""
    for channel in range(1, netlist.OUTPUT_COUNT + 1):
        net = nets["DO%d" % channel]
        switch = _pad(footprints, "Q%d" % (channel + 1), "3").GetPosition()
        clamp = _pad(footprints, "D%d" % (channel + 8), "1").GetPosition()
        terminal = _pad(footprints, "J3", "%d" % (channel + 1)).GetPosition()
        lane = pcbnew.VECTOR2I(clamp.x, switch.y)
        points = [switch, lane, clamp,
                  pcbnew.VECTOR2I(clamp.x, terminal.y), terminal]
        for first, second in zip(points, points[1:]):
            if first == second:
                continue
            _add_track(board, first, second, pcbnew.F_Cu, net,
                       POWER_TRACK_WIDTH_MM)


def _route_supply_return(board, footprints, nets):
    """The supply return terminal to the reverse-blocking device."""
    net = nets[netlist.SUPPLY_RETURN_NET]
    terminal = _pad(footprints, "J1", "2").GetPosition()
    drain = _pad(footprints, "Q1", "3").GetPosition()
    clamp = _pad(footprints, "D1", "1").GetPosition()
    corner = pcbnew.VECTOR2I(drain.x, terminal.y)
    for first, second in ((terminal, corner), (corner, drain),
                          (corner, pcbnew.VECTOR2I(clamp.x, terminal.y)),
                          (pcbnew.VECTOR2I(clamp.x, terminal.y), clamp)):
        if first == second:
            continue
        _add_track(board, first, second, pcbnew.F_Cu, net,
                   FIELD_TRACK_WIDTH_MM)


def fill_zones(board):
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    return board


def build(with_copper=True):
    """The board.

    `with_copper=False` produces the same placement with no pours: the
    placement search refuses a board that already carries copper, because
    moving a footprint would leave its copper behind. Everything conductive
    is generated from the accepted poses afterwards, so the two forms cannot
    disagree about where a part is.
    """
    board = pcbnew.CreateEmptyBoard()
    _design_settings(board)
    nets = _nets(board)
    pin_net = netlist.pin_to_net()

    footprints = {}
    placed = fixed_placements()
    for reference, (x, y, rotation) in sorted(placed.items()):
        part = netlist.PARTS[reference]
        if not part["footprint"]:
            continue
        footprints[reference] = _load(
            board, reference, part, x, y, rotation, pin_net, nets)

    _add_outline(board)
    if with_copper:
        _add_pours(board, nets)
        _route_bus_pair(board, footprints, nets)
        _route_termination_centre(board, footprints, nets)
        _route_converter_input(board, footprints, nets)
        _route_switch_node(board, footprints, nets)
        _route_field_supply(board, footprints, nets)
        _route_field_outputs(board, footprints, nets)
        _route_supply_return(board, footprints, nets)
        _stitch_grounds(board, footprints, nets)
    _add_silkscreen(board, footprints)
    return board, footprints


# ---------------------------------------------------------------------------
# silkscreen

SILK_LAYER = pcbnew.F_SilkS
SILK_TEXT_MM = 1.2
SILK_THICKNESS_MM = 0.2
RATING_Y_MM = 34.5
RATING_X_MM = 12.0
PROBE_LABEL_OFFSET_MM = 2.0


def _text(board, value, x, y, size_mm=SILK_TEXT_MM, layer=None):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(_point(x, y))
    item.SetLayer(SILK_LAYER if layer is None else layer)
    item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size_mm),
                                     pcbnew.FromMM(size_mm)))
    item.SetTextThickness(pcbnew.FromMM(SILK_THICKNESS_MM))
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(item)
    return item


def rating_text():
    """What the board is marked with, from what it claims, not from taste."""
    return "%.0f-%.0fV %.2fA/CH CAN-FD %.0fM" % (
        netlist.INPUT_SUPPLY["min_v"], netlist.INPUT_SUPPLY["max_v"],
        netlist.OUTPUT_CURRENT_RATING_A,
        netlist.DATA_PHASE_RATE_BPS / 1e6)


def probe_labels():
    """Which probe carries which net, from the netlist rather than a list."""
    pin_net = netlist.pin_to_net()
    return {reference: netlist.NET_MARKS[pin_net["%s.1" % reference]]
            for reference in netlist.PARTS if reference.startswith("TP")}


def connector_labels():
    """One label per connector contact, from the netlist's own contract."""
    labels = {}
    for reference, order in netlist.CONNECTOR_PIN_ORDER.items():
        labels[reference] = list(order)
    return labels


#: Which contacts are worth naming on the board itself, and where the name
#: goes relative to the contact. A field terminal that is wired the wrong way
#: round is the one mistake the connector cannot prevent, so every field
#: contact is named; the two link headers and the programming header are
#: named as a whole because their pin order is on the drawing, not in the
#: field.
LABELLED_CONNECTORS = ("J1", "J2", "J3", "J4")
CONNECTOR_LABEL_OFFSET_MM = 7.0
SILK_MIN_TEXT_MM = 1.0


def _add_silkscreen(board, footprints):
    _text(board, rating_text(), RATING_X_MM, RATING_Y_MM,
          size_mm=SILK_MIN_TEXT_MM)
    placed = fixed_placements()
    for reference, net in sorted(probe_labels().items()):
        x, y, _ = placed[reference]
        _text(board, net, x, y + PROBE_LABEL_OFFSET_MM,
              size_mm=SILK_MIN_TEXT_MM)
    for reference in LABELLED_CONNECTORS:
        functions = netlist.CONNECTOR_PIN_ORDER[reference]
        _x, y, rotation = placed[reference]
        inboard = 1.0 if rotation == 0.0 else -1.0
        for index, function in enumerate(functions):
            _text(board, netlist.CONNECTOR_CONTACT_MARKS[function],
                  connector_pin_x(reference, index + 1),
                  y + inboard * CONNECTOR_LABEL_OFFSET_MM,
                  size_mm=SILK_MIN_TEXT_MM)
    for reference, label, dx, dy in (
            ("J5", "SWD", 0.0, 3.2),
            ("J6", "TERM H", 0.0, -3.4),
            ("J7", "TERM L", 0.0, -3.4)):
        x, y, _rotation = placed[reference]
        _text(board, label, x + dx, y + dy, size_mm=SILK_MIN_TEXT_MM)


def write(path=None):
    """Write the board, then rewrite the project it belongs to.

    Saving a board rewrites the project file beside it with KiCad's own
    defaults, which is how the rule severities this board declares as
    warnings would become ignores. The project is therefore regenerated from
    the design source afterwards, every time, rather than left as whatever
    the save left behind.
    """
    from . import build as _build
    board, _ = build()
    fill_zones(board)
    target = BOARD_PATH if path is None else path
    pcbnew.SaveBoard(target, board)
    if path is None:
        _build.write_project()
    return target


def write_placement_board(path):
    board, _ = build(with_copper=False)
    pcbnew.SaveBoard(path, board)
    return path


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
