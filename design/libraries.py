"""The symbols and land patterns KiCad does not ship, generated from drawings.

Every dimension below is quoted from the package drawing named beside it, so
a reader can check the land pattern against the same document the footprint
was drawn from rather than against a remembered number. Where a vendor states
a recommended land pattern, that pattern is used; where none is stated, the
choice is this board's and says so.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_NAME = "CanFdNode"
SYMBOL_LIB_PATH = os.path.join(REPO_ROOT, "library",
                               LIBRARY_NAME + ".kicad_sym")
FOOTPRINT_DIR = os.path.join(REPO_ROOT, "library", LIBRARY_NAME + ".pretty")
SYM_LIB_TABLE = os.path.join(REPO_ROOT, "sym-lib-table")
FP_LIB_TABLE = os.path.join(REPO_ROOT, "fp-lib-table")

SYMBOL_LIB_VERSION = "20251024"
FOOTPRINT_VERSION = "20260206"
GENERATOR = "can-fd-node-design-source"

# TI SLLSES7D table 6-1, D (SOIC) package, "V" suffix column: the level
# shifting supply replaces the no-connect at pin 5, which is the only
# difference from the non-V devices and the reason this part was chosen.
TRANSCEIVER_SYMBOL_NAME = "TCAN1042HGV"
TRANSCEIVER_PINS = [("1", "TXD", "input", "left"),
                    ("4", "RXD", "output", "left"),
                    ("8", "STB", "input", "left"),
                    ("3", "VCC", "power_in", "top"),
                    ("5", "VIO", "power_in", "top"),
                    ("2", "GND", "power_in", "bottom"),
                    ("7", "CANH", "bidirectional", "right"),
                    ("6", "CANL", "bidirectional", "right")]
TRANSCEIVER_DATASHEET = "https://www.ti.com/lit/ds/symlink/tcan1042h.pdf"

# MPS MP2459 Rev. 1.1, pin functions table: TSOT23-6 is BST, GND, FB, EN, IN,
# SW on pins 1 to 6.
CONVERTER_SYMBOL_NAME = "MP2459"
CONVERTER_PINS = [("5", "IN", "power_in", "left"),
                  ("4", "EN", "input", "left"),
                  ("3", "FB", "input", "left"),
                  ("1", "BST", "passive", "right"),
                  ("6", "SW", "output", "right"),
                  ("2", "GND", "power_in", "bottom")]
CONVERTER_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                       "2304140030.pdf")

# Holtek HT75Rxx-1 Rev. 1.01, pin diagram: SOT89 is GND, VIN, VOUT on pins
# 1, 2, 3. The regulator output is the only source on the logic rail, so it
# is declared power_out and that rail carries no separate power flag.
REGULATOR_SYMBOL_NAME = "HT75Rxx-1"
REGULATOR_PINS = [("2", "VIN", "power_in", "left"),
                  ("3", "VOUT", "power_out", "right"),
                  ("1", "GND", "power_in", "bottom")]
REGULATOR_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                       "59abfa7ca0c1b0cd081d8e8f60c28ed0.pdf")

# ST DS12789 Rev 2, front-page internal schematic: two bidirectional
# suppressors from pins 1 and 2 to the common pin 3.
BUS_PROTECTOR_SYMBOL_NAME = "ESDCAN05-2BWY"
BUS_PROTECTOR_PINS = [("1", "IO1", "passive", "left"),
                      ("2", "IO2", "passive", "left"),
                      ("3", "GND", "passive", "bottom")]
BUS_PROTECTOR_DATASHEET = ("https://www.st.com/resource/en/datasheet/"
                           "esdcan05-2bwy.pdf")

# NCE6003X marking and pin assignment figure, SOT-23 top view: gate 1,
# source 2, drain 3.
BLOCKING_FET_SYMBOL_NAME = "NCE6003X"
BLOCKING_FET_DATASHEET = ("https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/"
                          "lcsc/2201121630.pdf")

# WST6066A SOT-23-3L pin configuration figure: gate and source on the two-pin
# side, drain opposite, which is the same numbering.
OUTPUT_FET_SYMBOL_NAME = "WST6066A"
OUTPUT_FET_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                        "fa81b0d9ae88480fa681d4eacf953c2b.pdf")

FET_PINS = [("1", "G", "input", "left"),
            ("2", "S", "passive", "bottom"),
            ("3", "D", "passive", "top")]

# DORABO DB128V-5.08-XXP-C-S customer drawing, 2022-10-27, rev T0-1: PCB hole
# diameter 1.60, pitch 5.08, pin 0.80 x 1.00, body N x 5.08 long by 10.20
# deep by 14.00 high, standing 3.50 off the board. The drawing states the
# hole but no annulus, so the 0.50 ring below is this board's choice.
TERMINAL_FAMILY = "DB128V-5.08"
TERMINAL_PITCH_MM = 5.08
TERMINAL_DRILL_MM = 1.60
TERMINAL_PAD_DIAMETER_MM = 2.60
TERMINAL_BODY_DEPTH_MM = 10.20
TERMINAL_PIN_TO_ENTRY_FACE_MM = 5.00
TERMINAL_COURTYARD_MARGIN_MM = 0.25
TERMINAL_POSITIONS = (2, 3, 5)

# YXC YSX531SL, "Recommended Land Pattern": four 2.0 x 1.2 pads with a 1.7
# horizontal gap and a 1.0 vertical gap, so centres lie on 3.7 by 2.2. Body
# 5.00 x 3.20 x 0.9 max. Pads 1 and 3 are the crystal, 2 and 4 the case.
CRYSTAL_FOOTPRINT_NAME = "Crystal_YXC_YSX531SL_5.0x3.2mm"
CRYSTAL_PAD_MM = (2.0, 1.2)
CRYSTAL_PAD_PITCH_MM = (3.7, 2.2)
CRYSTAL_BODY_MM = (5.0, 3.2)
CRYSTAL_COURTYARD_MARGIN_MM = 0.25

# Sunlord SWPA series catalogue (revised 2023/06/01), external dimensions
# table: the 5040 body is 5.0 x 5.0 x 4.0. The catalogue's land pattern is a
# figure rather than a dimensioned drawing, so the pads below are this
# board's choice: two 1.8 x 4.2 lands on 4.4 centres, which covers the
# terminations of a 5 x 5 wire-wound part with the usual 0.3 toe.
INDUCTOR_FOOTPRINT_NAME = "Inductor_Sunlord_SWPA5040"
INDUCTOR_PAD_MM = (1.8, 4.2)
INDUCTOR_PAD_PITCH_MM = 4.4
INDUCTOR_BODY_MM = (5.0, 5.0)
INDUCTOR_COURTYARD_MARGIN_MM = 0.25

# LUTE 1812L series, dimension table: body 4.37-4.73 long by 3.07-3.41 wide,
# pad width 0.60-1.50 with a 0.30 to 0.20 gap. The series states no
# recommended land pattern, so the two 1.80 x 3.40 lands on a 3.20 gap below
# are this board's choice, sized to cover the widest body and the longest
# termination.
PTC_FOOTPRINT_NAME = "PTC_1812_LUTE_1812L"
PTC_PAD_MM = (1.80, 3.40)
PTC_PAD_GAP_MM = 3.20
PTC_BODY_MM = (4.73, 3.41)
PTC_COURTYARD_MARGIN_MM = 0.25

# The five connectors, drawn with their functions on the pins rather than as
# numbered generic terminals. The board's contract is which contact carries
# what - the brief fixes the bus pair's position, and a plug that mates
# mechanically but not in this order damages what it is wired to - so the
# order is on the symbol where a reader sees it, not only in a table.
CONNECTOR_SYMBOLS = {
    "SupplyInput_1x02": ["V24_IN", "RETURN"],
    "BusConnector_1x03": ["CAN_GND", "CANL", "CANH"],
    "OutputConnector_1x05": ["VFIELD", "DO1", "DO2", "DO3", "DO4"],
    "InputConnector_1x05": ["GND", "DI1", "DI2", "DI3", "DI4"],
    "DebugHeader_1x05": ["+3V3", "SWDIO", "SWCLK", "NRST", "GND"],
}

# A termination link: one leg of the split termination passes through it, and
# there is one on each side of the bus pair. Two headers rather than one is
# what keeps either leg from having to cross the pair to reach the other.
TERMINATION_LINK_SYMBOL_NAME = "TerminationLink_1x02"
TERMINATION_LINK_PINS = ["LEG", "SPLIT"]

# Jingdao SMF series, "The recommended mounting pad size": two 1.2 x 1.2 pads
# with a 2.0 gap, so 3.2 between centres. Body D is 2.6-2.9 long and E is
# 1.7-1.9 wide.
SOD123FL_FOOTPRINT_NAME = "D_SOD-123FL_1.2x1.2mm_P3.2mm"
SOD123FL_PAD_MM = (1.20, 1.20)
SOD123FL_PAD_PITCH_MM = 3.20
SOD123FL_BODY_MM = (2.90, 1.90)
SOD123FL_COURTYARD_MARGIN_MM = 0.25


# ---------------------------------------------------------------------------
# symbols

def _property(key, value, index, hide):
    hidden = "\n\t\t\t(hide yes)" if hide else ""
    return ('\t\t(property "%s" "%s"\n\t\t\t(at 0 %.2f 0)%s\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            % (key, value, 17.78 - 2.54 * index, hidden))


_SIDE_ANGLE = {"left": 0, "right": 180, "top": 270, "bottom": 90}


def _pin(number, name, electrical_type, x, y, angle, length=2.54):
    return (
        '\t\t\t(pin %s line\n\t\t\t\t(at %.2f %.2f %d)\n'
        '\t\t\t\t(length %.2f)\n'
        '\t\t\t\t(name "%s"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n'
        '\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n'
        '\t\t\t\t)\n'
        '\t\t\t\t(number "%s"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n'
        '\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n'
        '\t\t\t\t)\n\t\t\t)\n'
        % (electrical_type, x, y, angle, length, name, number))


def _rectangle(x1, y1, x2, y2):
    return ('\t\t\t(rectangle\n\t\t\t\t(start %.2f %.2f)\n'
            '\t\t\t\t(end %.2f %.2f)\n'
            '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type '
            'default)\n\t\t\t\t)\n'
            '\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n'
            '\t\t\t)\n' % (x1, y1, x2, y2))


def _boxed_symbol(name, pins, datasheet, description, half_width=7.62,
                  half_height=None, reference="U"):
    """A rectangle with pins on the sides named in the pin list."""
    by_side = {"left": [], "right": [], "top": [], "bottom": []}
    for number, pin_name, electrical_type, side in pins:
        by_side[side].append((number, pin_name, electrical_type))
    rows = max(len(by_side["left"]), len(by_side["right"]))
    if half_height is None:
        half_height = max(5.08, 1.27 + 2.54 * rows / 2.0)
    body = [_rectangle(-half_width, half_height, half_width, -half_height)]
    for side in ("left", "right"):
        entries = by_side[side]
        top = 2.54 * (len(entries) - 1) / 2.0
        for index, (number, pin_name, electrical_type) in enumerate(entries):
            y = top - 2.54 * index
            x = -half_width - 2.54 if side == "left" else half_width + 2.54
            body.append(_pin(number, pin_name, electrical_type, x, y,
                             _SIDE_ANGLE[side]))
    for side in ("top", "bottom"):
        entries = by_side[side]
        left = -2.54 * (len(entries) - 1) / 2.0
        for index, (number, pin_name, electrical_type) in enumerate(entries):
            x = left + 2.54 * index
            y = half_height + 2.54 if side == "top" else -half_height - 2.54
            body.append(_pin(number, pin_name, electrical_type, x, y,
                             _SIDE_ANGLE[side]))
    return _symbol(name, datasheet, description, body,
                   reference=reference)


def _symbol(name, datasheet, description, body_items,
            reference="U", value=None):
    text = '\t(symbol "%s"\n' % name
    text += '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n'
    text += '\t\t(on_board yes)\n'
    text += _property("Reference", reference, 0, False)
    text += _property("Value", value or name, 1, False)
    text += _property("Footprint", "", 2, True)
    text += _property("Datasheet", datasheet, 3, True)
    text += _property("Description", description, 4, True)
    text += '\t\t(symbol "%s_1_1"\n' % name
    text += "".join(body_items)
    text += "\t\t)\n\t)\n"
    return text


def _connector_symbol(name, pin_names):
    """A connector whose pins carry the function each contact is wired to."""
    pins = [(str(index + 1), pin_name, "passive", "right")
            for index, pin_name in enumerate(pin_names)]
    return _boxed_symbol(name, pins, "", "board connector, %d positions"
                         % len(pin_names), half_width=5.08, reference="J")


def _fet_symbol(name, datasheet, description):
    """An enhancement N-channel MOSFET whose pin numbers are the package's.

    Drawn as a box rather than as a transistor glyph: the schematic this
    board generates carries no wires, so the shape communicates nothing the
    pin names do not, and a box keeps every generated symbol on one
    footing.
    """
    return _boxed_symbol(name, FET_PINS, datasheet, description,
                         half_width=5.08, half_height=5.08,
                         reference="Q")


def symbol_document():
    parts = [
        '(kicad_symbol_lib\n\t(version %s)\n\t(generator "%s")\n'
        % (SYMBOL_LIB_VERSION, GENERATOR)]
    parts.append(_boxed_symbol(
        TRANSCEIVER_SYMBOL_NAME, TRANSCEIVER_PINS, TRANSCEIVER_DATASHEET,
        "CAN FD transceiver, 5 V bus supply with separate I/O supply"))
    parts.append(_boxed_symbol(
        CONVERTER_SYMBOL_NAME, CONVERTER_PINS, CONVERTER_DATASHEET,
        "55 V 0.5 A fixed-frequency step-down converter"))
    parts.append(_boxed_symbol(
        REGULATOR_SYMBOL_NAME, REGULATOR_PINS, REGULATOR_DATASHEET,
        "30 V 150 mA low-dropout linear regulator", half_width=5.08))
    parts.append(_boxed_symbol(
        BUS_PROTECTOR_SYMBOL_NAME, BUS_PROTECTOR_PINS,
        BUS_PROTECTOR_DATASHEET,
        "dual-line bidirectional transient suppressor for CAN",
        half_width=5.08, reference="D"))
    parts.append(_fet_symbol(
        BLOCKING_FET_SYMBOL_NAME, BLOCKING_FET_DATASHEET,
        "60 V 3 A N-channel MOSFET"))
    parts.append(_fet_symbol(
        OUTPUT_FET_SYMBOL_NAME, OUTPUT_FET_DATASHEET,
        "60 V 2.1 A N-channel MOSFET, on-resistance stated at 2.5 V"))
    for name, names in sorted(CONNECTOR_SYMBOLS.items()):
        parts.append(_connector_symbol(name, names))
    parts.append(_connector_symbol(TERMINATION_LINK_SYMBOL_NAME,
                                   TERMINATION_LINK_PINS))
    parts.append(")\n")
    return "".join(parts)


def write_symbols():
    os.makedirs(os.path.dirname(SYMBOL_LIB_PATH), exist_ok=True)
    with open(SYMBOL_LIB_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(symbol_document())
    return SYMBOL_LIB_PATH


# ---------------------------------------------------------------------------
# footprints

def _fp_text(kind, value, x, y, layer):
    return ('\t(property "%s" "%s"\n\t\t(at %.4f %.4f 0)\n'
            '\t\t(layer "%s")\n\t\t(uuid "")\n'
            '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n'
            '\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n'
            % (kind, value, x, y, layer))


def _line(x1, y1, x2, y2, layer, width=0.12):
    return ('\t(fp_line\n\t\t(start %.4f %.4f)\n\t\t(end %.4f %.4f)\n'
            '\t\t(stroke\n\t\t\t(width %.3f)\n\t\t\t(type solid)\n\t\t)\n'
            '\t\t(layer "%s")\n\t\t(uuid "")\n\t)\n'
            % (x1, y1, x2, y2, width, layer))


def _rect_outline(x1, y1, x2, y2, layer, width=0.12):
    return (_line(x1, y1, x2, y1, layer, width)
            + _line(x2, y1, x2, y2, layer, width)
            + _line(x2, y2, x1, y2, layer, width)
            + _line(x1, y2, x1, y1, layer, width))


def _smd_pad(number, x, y, width, height, roundrect=True):
    shape = "roundrect" if roundrect else "rect"
    ratio = '\n\t\t(roundrect_rratio 0.25)' if roundrect else ""
    return ('\t(pad "%s" smd %s\n\t\t(at %.4f %.4f)\n\t\t(size %.4f %.4f)\n'
            '\t\t(layers "F.Cu" "F.Paste" "F.Mask")%s\n\t\t(uuid "")\n\t)\n'
            % (number, shape, x, y, width, height, ratio))


def _th_pad(number, x, y, diameter, drill, shape="circle"):
    return ('\t(pad "%s" thru_hole %s\n\t\t(at %.4f %.4f)\n'
            '\t\t(size %.4f %.4f)\n\t\t(drill %.4f)\n'
            '\t\t(layers "*.Cu" "*.Mask")\n\t\t(uuid "")\n\t)\n'
            % (number, shape, x, y, diameter, diameter, drill))


def _footprint(name, description, tags, body, through_hole=False):
    attr = "through_hole" if through_hole else "smd"
    text = ('(footprint "%s"\n\t(version %s)\n\t(generator "%s")\n'
            '\t(layer "F.Cu")\n\t(descr "%s")\n\t(tags "%s")\n'
            '\t(attr %s)\n'
            % (name, FOOTPRINT_VERSION, GENERATOR, description, tags, attr))
    text += _fp_text("Reference", "REF**", 0, -0.5, "F.SilkS")
    text += _fp_text("Value", name, 0, 0.5, "F.Fab")
    text += body
    text += ")\n"
    return text


def terminal_block_footprint(positions):
    """One land pattern per position count, from the same family drawing."""
    name = "TerminalBlock_%s_1x%02d_P%.2fmm" % (
        TERMINAL_FAMILY, positions, TERMINAL_PITCH_MM)
    span = TERMINAL_PITCH_MM * (positions - 1)
    left = -span / 2.0
    body_left = left - (TERMINAL_PITCH_MM / 2.0)
    body_right = -body_left
    # The wire enters on the -Y side; the pin row sits
    # TERMINAL_PIN_TO_ENTRY_FACE_MM behind that face.
    body_front = -TERMINAL_PIN_TO_ENTRY_FACE_MM
    body_back = TERMINAL_BODY_DEPTH_MM - TERMINAL_PIN_TO_ENTRY_FACE_MM
    body = ""
    for index in range(positions):
        x = left + TERMINAL_PITCH_MM * index
        body += _th_pad("%d" % (index + 1), x, 0.0,
                        TERMINAL_PAD_DIAMETER_MM, TERMINAL_DRILL_MM,
                        "rect" if index == 0 else "circle")
    body += _rect_outline(body_left, body_front, body_right, body_back,
                          "F.Fab")
    body += _rect_outline(body_left - 0.15, body_front - 0.15,
                          body_right + 0.15, body_back + 0.15, "F.SilkS")
    margin = TERMINAL_COURTYARD_MARGIN_MM
    body += _rect_outline(body_left - margin, body_front - margin,
                          body_right + margin, body_back + margin,
                          "F.CrtYd", 0.05)
    return name, _footprint(
        name,
        "DORABO %s %d-position screw terminal, 5.08 mm pitch, 1.60 mm holes"
        % (TERMINAL_FAMILY, positions),
        "terminal block screw 5.08mm", body, through_hole=True)


def crystal_footprint():
    name = CRYSTAL_FOOTPRINT_NAME
    dx = CRYSTAL_PAD_PITCH_MM[0] / 2.0
    dy = CRYSTAL_PAD_PITCH_MM[1] / 2.0
    width, height = CRYSTAL_PAD_MM
    body = ""
    for number, (x, y) in (("1", (-dx, dy)), ("2", (dx, dy)),
                           ("3", (dx, -dy)), ("4", (-dx, -dy))):
        body += _smd_pad(number, x, y, width, height)
    bx, by = CRYSTAL_BODY_MM[0] / 2.0, CRYSTAL_BODY_MM[1] / 2.0
    body += _rect_outline(-bx, -by, bx, by, "F.Fab")
    margin = CRYSTAL_COURTYARD_MARGIN_MM
    body += _rect_outline(-bx - margin, -by - margin, bx + margin,
                          by + margin, "F.CrtYd", 0.05)
    return name, _footprint(
        name,
        "YXC YSX531SL 5.0x3.2 mm four-pad crystal, pads 1 and 3 the crystal",
        "crystal smd 5032", body)


def inductor_footprint():
    name = INDUCTOR_FOOTPRINT_NAME
    width, height = INDUCTOR_PAD_MM
    dx = INDUCTOR_PAD_PITCH_MM / 2.0
    body = _smd_pad("1", -dx, 0.0, width, height)
    body += _smd_pad("2", dx, 0.0, width, height)
    bx, by = INDUCTOR_BODY_MM[0] / 2.0, INDUCTOR_BODY_MM[1] / 2.0
    body += _rect_outline(-bx, -by, bx, by, "F.Fab")
    margin = INDUCTOR_COURTYARD_MARGIN_MM
    body += _rect_outline(-bx - margin, -by - margin, bx + margin,
                          by + margin, "F.CrtYd", 0.05)
    return name, _footprint(
        name, "Sunlord SWPA5040 5.0x5.0x4.0 mm shielded power inductor",
        "inductor smd shielded", body)


def ptc_footprint():
    name = PTC_FOOTPRINT_NAME
    width, height = PTC_PAD_MM
    dx = (PTC_PAD_GAP_MM + width) / 2.0
    body = _smd_pad("1", -dx, 0.0, width, height)
    body += _smd_pad("2", dx, 0.0, width, height)
    bx, by = PTC_BODY_MM[0] / 2.0, PTC_BODY_MM[1] / 2.0
    body += _rect_outline(-bx, -by, bx, by, "F.Fab")
    margin = PTC_COURTYARD_MARGIN_MM
    body += _rect_outline(-bx - margin, -by - margin, bx + margin,
                          by + margin, "F.CrtYd", 0.05)
    return name, _footprint(
        name, "LUTE 1812L series 1812 resettable fuse", "ptc fuse 1812",
        body)


def sod123fl_footprint():
    name = SOD123FL_FOOTPRINT_NAME
    width, height = SOD123FL_PAD_MM
    dx = SOD123FL_PAD_PITCH_MM / 2.0
    body = _smd_pad("1", -dx, 0.0, width, height)
    body += _smd_pad("2", dx, 0.0, width, height)
    bx, by = SOD123FL_BODY_MM[0] / 2.0, SOD123FL_BODY_MM[1] / 2.0
    body += _rect_outline(-bx, -by, bx, by, "F.Fab")
    # the band end, which is pad 1: clear of the land, or the mark is on
    # the copper it is meant to identify
    mark_x = -(dx + width / 2.0 + 0.3)
    body += _line(mark_x, -by, mark_x, by, "F.SilkS", 0.2)
    margin = SOD123FL_COURTYARD_MARGIN_MM
    body += _rect_outline(-dx - width / 2.0 - margin, -by - margin,
                          dx + width / 2.0 + margin, by + margin,
                          "F.CrtYd", 0.05)
    return name, _footprint(
        name, "SOD-123FL, 1.2x1.2 mm pads on 3.2 mm centres",
        "diode smd sod-123fl", body)


def footprints():
    made = [crystal_footprint(), inductor_footprint(), ptc_footprint(),
            sod123fl_footprint()]
    made.extend(terminal_block_footprint(count)
                for count in TERMINAL_POSITIONS)
    return dict(made)


def write_footprints():
    os.makedirs(FOOTPRINT_DIR, exist_ok=True)
    written = []
    for name, text in sorted(footprints().items()):
        path = os.path.join(FOOTPRINT_DIR, name + ".kicad_mod")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# library tables

def sym_lib_table_text():
    return ('(sym_lib_table\n\t(version 7)\n'
            '\t(lib (name "%s")(type "KiCad")(uri '
            '"${KIPRJMOD}/library/%s.kicad_sym")(options "")(descr ""))\n)\n'
            % (LIBRARY_NAME, LIBRARY_NAME))


def fp_lib_table_text():
    return ('(fp_lib_table\n\t(version 7)\n'
            '\t(lib (name "%s")(type "KiCad")(uri '
            '"${KIPRJMOD}/library/%s.pretty")(options "")(descr ""))\n)\n'
            % (LIBRARY_NAME, LIBRARY_NAME))


def write_tables():
    for path, text in ((SYM_LIB_TABLE, sym_lib_table_text()),
                       (FP_LIB_TABLE, fp_lib_table_text())):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    return [SYM_LIB_TABLE, FP_LIB_TABLE]


def artifacts():
    """Every file this module owns, by path.

    The library is generated, so the question a reader has is whether the
    files in the tree are the ones this source produces and nothing else.
    That question is answerable only if the source can state its own output
    without writing it, which is what this is for.
    """
    made = {SYMBOL_LIB_PATH: symbol_document(),
            SYM_LIB_TABLE: sym_lib_table_text(),
            FP_LIB_TABLE: fp_lib_table_text()}
    for name, text in footprints().items():
        made[os.path.join(FOOTPRINT_DIR, name + ".kicad_mod")] = text
    return made


def write():
    return [write_symbols()] + write_footprints() + write_tables()


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
