"""Every part, every net, and the numbers the board declares about itself.

The board is a CAN-FD node on a 24 V industrial supply. Current enters at one
terminal pair, is clamped and reverse-blocked, and then splits three ways: to
the field output supply, to a step-down converter that feeds the transceiver,
and through that converter's regulator to the controller. The bus enters at
its own terminal, meets its protection and its switchable termination before
anything else, and reaches the controller only through the transceiver.

Reference blocks are contiguous so the layout can group a channel without a
second table: the four low-side outputs are Q2..Q5, their gate networks are
R26..R33, their clamps D9..D12; the four inputs are R14..R25 with D5..D8.
"""
from __future__ import annotations

import os

#: Field channels of each kind. The brief asks for four of each.
INPUT_COUNT = 4
OUTPUT_COUNT = 4

PROJECT_NAME = "can_fd_node"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYMBOL_LIBRARY_PATHS = (
    os.path.join(_REPO_ROOT, "library"),
    "/usr/share/kicad/symbols",
)

LIBRARY_NAME = "CanFdNode"

#: Controller pin each function lands on. LQFP-32 pin numbers from DS12589
#: table 12. The four inputs are on FT pins that are neither FT_c (whose
#: leakage is twenty times higher and whose thresholds differ) nor part of the
#: debug port (whose internal pull resistors are enabled out of reset, and
#: which the same datasheet says must be disabled to sustain more than 4 V).
INPUT_PINS = ("18", "26", "28", "30")
OUTPUT_PINS = ("5", "6", "7", "8")
TRANSCEIVER_STANDBY_PIN = "9"
STATUS_LED_PIN = "10"
CAN_RX_PIN = "21"
CAN_TX_PIN = "22"
SWDIO_PIN = "23"
SWCLK_PIN = "24"
OSC_IN_PIN = "2"
OSC_OUT_PIN = "3"
RESET_PIN = "4"
BOOT_PIN = "31"

#: What each of those pins is called and what peripheral it carries, so a
#: firmware author does not have to re-derive the mapping from the netlist.
MCU_PIN_FUNCTIONS = {
    "2": "PF0-OSC_IN", "3": "PF1-OSC_OUT", "4": "PG10-NRST",
    "5": "PA0", "6": "PA1", "7": "PA2", "8": "PA3", "9": "PA4",
    "10": "PA5", "18": "PA8", "21": "PA11/FDCAN1_RX",
    "22": "PA12/FDCAN1_TX", "23": "PA13/SWDIO", "24": "PA14/SWCLK",
    "26": "PB3", "28": "PB5", "30": "PB7", "31": "PB8-BOOT0",
}

#: Pins the LQFP-32 brings out that this board does not use.
MCU_UNUSED_PINS = ("11", "12", "13", "19", "20", "25", "27", "29")

#: Controller supply and ground pins, from the same table.
MCU_SUPPLY_PINS = ("1", "17")
MCU_ANALOG_SUPPLY_PIN = "15"
MCU_GROUND_PINS = ("16", "32")
MCU_ANALOG_GROUND_PIN = "14"


def _part(lib_id, footprint, value, mpn=None, manufacturer=None, lcsc=None,
          datasheet="", in_bom=True, on_board=True):
    return {
        "lib_id": lib_id,
        "footprint": footprint,
        "value": value,
        "mpn": mpn,
        "manufacturer": manufacturer,
        "lcsc": lcsc,
        "datasheet": datasheet,
        "in_bom": in_bom,
        "on_board": on_board,
    }


UNIROYAL = "UNI-ROYAL(Uniroyal Elec)"

#: Resistor values used on this board, and the catalogue part behind each as
#: (code, part number, manufacturer, footprint size). The two termination
#: resistors are 2512 because a bus line shorted to the field rail while this
#: node drives dominant puts more through them, continuously, than a smaller
#: part is rated for; everything else is 0603.
RESISTOR_PARTS = {
    "100R": ("C22775", "0603WAF1000T5E", UNIROYAL, "0603"),
    "470R": ("C23179", "0603WAF4700T5E", UNIROYAL, "0603"),
    "2.7k": ("C13167", "0603WAF2701T5E", UNIROYAL, "0603"),
    "10k": ("C25804", "0603WAF1002T5E", UNIROYAL, "0603"),
    "20k": ("C4184", "0603WAF2002T5E", UNIROYAL, "0603"),
    "23.7k": ("C22912", "0603WAF2372T5E", UNIROYAL, "0603"),
    "56k": ("C23206", "0603WAF5602T5E", UNIROYAL, "0603"),
    "100k": ("C25803", "0603WAF1003T5E", UNIROYAL, "0603"),
    "124k": ("C22788", "0603WAF1243T5E", UNIROYAL, "0603"),
    "470k": ("C23178", "0603WAF4703T5E", UNIROYAL, "0603"),
    "60.4R": ("C3994751", "RMCF2512FT60R4", "SEI(Stackpole Elec)", "2512"),
}

CAPACITOR_PARTS = {
    "15pF": ("C107037", "CC0603JRNPO9BN150", "YAGEO",
             "Capacitor_SMD:C_0603_1608Metric", "Device:C"),
    "4.7nF": ("C115052", "CC0603KRX7R0BB472", "YAGEO",
              "Capacitor_SMD:C_0603_1608Metric", "Device:C"),
    "10nF": ("C107059", "CC0603KRX7R0BB103", "YAGEO",
             "Capacitor_SMD:C_0603_1608Metric", "Device:C"),
    "100nF": ("C113803", "CC0603KRX7R0BB104", "YAGEO",
              "Capacitor_SMD:C_0603_1608Metric", "Device:C"),
    "1uF": ("C106858", "CC0603KRX7R8BB105", "YAGEO",
            "Capacitor_SMD:C_0603_1608Metric", "Device:C"),
    "1uF/100V": ("C70463", "CC1206KKX7R0BB105", "YAGEO",
                 "Capacitor_SMD:C_1206_3216Metric", "Device:C"),
    "10uF": ("C326595", "CC0805KKX7R7BB106", "YAGEO",
             "Capacitor_SMD:C_0805_2012Metric", "Device:C"),
    "47uF": ("C47023121", "RVT63V47M6X8", "jieerrui",
             "Capacitor_SMD:CP_Elec_6.3x7.7", "Device:C_Polarized"),
}

#: Where every resistor goes. Channel blocks are four consecutive numbers.
_RESISTOR_VALUES = {
    1: "100k",     # reverse-blocking gate pull-up
    2: "124k",     # converter feedback, upper
    3: "23.7k",    # converter feedback, lower
    4: "470k",     # converter enable divider, upper
    5: "56k",      # converter enable divider, lower
    6: "2.7k",     # logic-rail bleed
    7: "10k",      # boot-mode pull-down
    8: "10k",      # transceiver standby pull-down
    9: "60.4R",    # termination, CANH leg
    10: "60.4R",   # termination, CANL leg
    11: "470R",    # status indicator
    12: "100R",    # debug data series
    13: "100R",    # debug clock series
}
for _base, _value, _count in ((14, "100k", INPUT_COUNT),
                              (18, "20k", INPUT_COUNT),
                              (22, "10k", INPUT_COUNT),
                              (26, "100R", OUTPUT_COUNT),
                              (30, "100k", OUTPUT_COUNT)):
    for _offset in range(_count):
        _RESISTOR_VALUES[_base + _offset] = _value

_CAPACITOR_VALUES = {
    1: "47uF",    # input reservoir
    2: "100nF",   # input high-frequency bypass
    3: "100nF",   # converter bootstrap
    4: "1uF/100V",  # converter input
    5: "1uF/100V",  # converter input
    6: "10uF",    # converter output
    7: "10uF",    # converter output
    8: "100nF",   # converter output high-frequency bypass
    9: "10uF",    # regulator output
    10: "100nF",  # regulator output high-frequency bypass
    11: "100nF",  # controller supply, pin 1
    12: "100nF",  # controller supply, pin 17
    13: "100nF",  # controller analogue supply
    14: "1uF",    # controller analogue supply bulk
    15: "100nF",  # reset
    16: "15pF",   # crystal load
    17: "15pF",   # crystal load
    18: "100nF",  # transceiver bus supply
    19: "100nF",  # transceiver interface supply
    20: "4.7nF",  # split-termination centre
}
for _offset in range(INPUT_COUNT):
    _CAPACITOR_VALUES[21 + _offset] = "10nF"   # input filter


#: Metric land-pattern code of each imperial resistor size used.
RESISTOR_METRIC_CODE = {"0603": "1608", "2512": "6332"}


def _resistor(value):
    lcsc, mpn, manufacturer, size = RESISTOR_PARTS[value]
    footprint = "Resistor_SMD:R_%s_%sMetric" % (
        size, RESISTOR_METRIC_CODE[size])
    return _part("Device:R", footprint, value, mpn, manufacturer, lcsc)


def _capacitor(value):
    lcsc, mpn, manufacturer, footprint, lib_id = CAPACITOR_PARTS[value]
    return _part(lib_id, footprint, value, mpn, manufacturer, lcsc)


def _parts():
    parts = {
        "U1": _part(
            "MCU_ST_STM32G4:STM32G431KBTx",
            "Package_QFP:LQFP-32_7x7mm_P0.8mm",
            "STM32G431KBT6", "STM32G431KBT6", "STMicroelectronics",
            "C529357"),
        "U2": _part(
            "%s:TCAN1042HGV" % LIBRARY_NAME,
            "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            "TCAN1042HGVDR", "TCAN1042HGVDR", "Texas Instruments",
            "C124014"),
        "U3": _part(
            "%s:MP2459" % LIBRARY_NAME,
            "Package_TO_SOT_SMD:TSOT-23-6",
            "MP2459GJ-Z", "MP2459GJ-Z", "Monolithic Power Systems",
            "C39578"),
        "U4": _part(
            "%s:HT75Rxx-1" % LIBRARY_NAME,
            "Package_TO_SOT_SMD:SOT-89-3",
            "HT75R33-1A", "HT75R33-1A", "Holtek Semiconductor",
            "C53223865"),
        "Q1": _part(
            "%s:NCE6003X" % LIBRARY_NAME,
            "Package_TO_SOT_SMD:SOT-23",
            "NCE6003X", "NCE6003X", "Wuxi NCE Power Semiconductor",
            "C2934580"),
        "D1": _part(
            "Device:D_TVS", "Diode_SMD:D_SMA",
            "SMAJ30CA", "SMAJ30CA", "MDD(Microdiode Semiconductor)",
            "C110043"),
        "D2": _part(
            "Device:D_Zener", "Diode_SMD:D_SOD-123",
            "BZT52C12", "BZT52C12", "MDD(Microdiode Semiconductor)",
            "C173429"),
        "D3": _part(
            "Device:D_Schottky", "Diode_SMD:D_SMA",
            "B1100", "B1100-13-F", "Diodes Incorporated", "C110106"),
        "D4": _part(
            "%s:ESDCAN05-2BWY" % LIBRARY_NAME,
            "Package_TO_SOT_SMD:SOT-323_SC-70",
            "ESDCAN05-2BWY", "ESDCAN05-2BWY", "STMicroelectronics",
            "C1973137"),
        "D13": _part(
            "Device:LED", "LED_SMD:LED_0603_1608Metric",
            "KT-0603R", "KT-0603R", "Hubei KENTO Elec", "C2286"),
        "L1": _part(
            "Device:L", "%s:Inductor_Sunlord_SWPA5040" % LIBRARY_NAME,
            "47uH", "SWPA5040S470MT", "Sunlord", "C86617"),
        "Y1": _part(
            "Device:Crystal_GND24",
            "%s:Crystal_YXC_YSX531SL_5.0x3.2mm" % LIBRARY_NAME,
            "8MHz", "XL1EL89CMI-111YLC-8M", "YXC Crystal Oscillators",
            "C19711736"),
        "F1": _part(
            "Device:Polyfuse", "%s:PTC_1812_LUTE_1812L" % LIBRARY_NAME,
            "1812L200/33GR", "1812L200/33GR", "LUTE", "C18198343"),
        "J6": _part(
            "%s:TerminationLink_1x02" % LIBRARY_NAME,
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
            "KH-2.54PH180-1X2P-L11.5", "KH-2.54PH180-1X2P-L11.5",
            "Shenzhen Kinghelm Elec", "C2905434"),
        "J7": _part(
            "%s:TerminationLink_1x02" % LIBRARY_NAME,
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
            "KH-2.54PH180-1X2P-L11.5", "KH-2.54PH180-1X2P-L11.5",
            "Shenzhen Kinghelm Elec", "C2905434"),
        "J1": _part(
            "%s:SupplyInput_1x02" % LIBRARY_NAME,
            "%s:TerminalBlock_DB128V-5.08_1x02_P5.08mm" % LIBRARY_NAME,
            "DB128V-5.08-2P-GN-S", "DB128V-5.08-2P-GN-S", "DORABO",
            "C2915639"),
        "J2": _part(
            "%s:BusConnector_1x03" % LIBRARY_NAME,
            "%s:TerminalBlock_DB128V-5.08_1x03_P5.08mm" % LIBRARY_NAME,
            "DB128V-5.08-3P-GN-S", "DB128V-5.08-3P-GN-S", "DORABO",
            "C2915640"),
        "J5": _part(
            "%s:DebugHeader_1x05" % LIBRARY_NAME,
            "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
            "KH-2.54PH180-1X5P-L11.5", "KH-2.54PH180-1X5P-L11.5",
            "Shenzhen Kinghelm Elec", "C2932699"),
    }
    for reference, symbol in (("J3", "OutputConnector_1x05"),
                              ("J4", "InputConnector_1x05")):
        parts[reference] = _part(
            "%s:%s" % (LIBRARY_NAME, symbol),
            "%s:TerminalBlock_DB128V-5.08_1x05_P5.08mm" % LIBRARY_NAME,
            "DB128V-5.08-5P-GN-S", "DB128V-5.08-5P-GN-S", "DORABO",
            "C2927513")
    for channel in range(1, OUTPUT_COUNT + 1):
        parts["Q%d" % (channel + 1)] = _part(
            "%s:WST6066A" % LIBRARY_NAME,
            "Package_TO_SOT_SMD:SOT-23",
            "WST6066A", "WST6066A", "Winsok Semicon", "C148352")
        parts["D%d" % (channel + 8)] = _part(
            "Device:D_TVS",
            "%s:D_SOD-123FL_1.2x1.2mm_P3.2mm" % LIBRARY_NAME,
            "SMF30A", "SMF30A", "Shandong Jingdao Microelectronics",
            "C364281")
    for channel in range(1, INPUT_COUNT + 1):
        parts["D%d" % (channel + 4)] = _part(
            "Device:D", "Diode_SMD:D_SOD-123",
            "1N4148W", "1N4148W", "ST(Semtech)", "C81598")
    for index, value in sorted(_RESISTOR_VALUES.items()):
        parts["R%d" % index] = _resistor(value)
    for index, value in sorted(_CAPACITOR_VALUES.items()):
        parts["C%d" % index] = _capacitor(value)
    for index in range(1, 10):
        parts["TP%d" % index] = _part(
            "Connector:TestPoint", "TestPoint:TestPoint_Pad_D1.0mm",
            "TestPoint", in_bom=False)
    for index in range(1, 5):
        parts["H%d" % index] = _part(
            "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3",
            "MountingHole_M3", in_bom=False)
    for index in range(1, 6):
        parts["#FLG%d" % index] = _part(
            "power:PWR_FLAG", "", "PWR_FLAG", in_bom=False, on_board=False)
    return parts


PARTS = _parts()


# ---------------------------------------------------------------------------
# nets

#: The one deliberate break in the current path: the reverse-blocking device
#: sits in the return, so the supply's return terminal and the board's
#: reference are two different nodes and everything on the board references
#: the second one. Putting the device here rather than in the positive rail
#: is what lets the bus connector's reference pin be the board's own ground,
#: which is what the discharge path needs.
SUPPLY_RETURN_NET = "RTN"
GROUND_NET = "GND"
INPUT_RAIL_NET = "V24"
FIELD_SUPPLY_NET = "VFIELD"
INTERMEDIATE_RAIL_NET = "+5V"
LOGIC_RAIL_NET = "+3V3"

#: Connector pin each function occupies. CANH and CANL are adjacent with
#: nothing between them, which the brief requires and the contract gate
#: checks.
CONNECTOR_FUNCTION_NETS = {
    "J1": {"V24_IN": INPUT_RAIL_NET, "RETURN": SUPPLY_RETURN_NET},
    "J2": {"CAN_GND": GROUND_NET, "CANL": "CANL", "CANH": "CANH"},
    "J3": {"VFIELD": FIELD_SUPPLY_NET, "DO1": "DO1", "DO2": "DO2",
           "DO3": "DO3", "DO4": "DO4"},
    "J4": {"GND": GROUND_NET, "DI1": "DI1", "DI2": "DI2", "DI3": "DI3",
           "DI4": "DI4"},
    "J5": {"+3V3": LOGIC_RAIL_NET, "SWDIO": "SWD_DIO", "SWCLK": "SWD_CLK",
           "NRST": "NRST", "GND": GROUND_NET},
    "J6": {"CANH_LEG": "TERM_H", "SPLIT": "TERM_SPLIT"},
    "J7": {"CANL_LEG": "TERM_L", "SPLIT": "TERM_SPLIT"},
}

#: What each contact is marked with on the board itself. The mark is short
#: enough to fit between two contacts on a 5.08 pitch and is tied to the
#: function it names, so a mark and a contract cannot drift apart.
CONNECTOR_CONTACT_MARKS = {
    "V24_IN": "V+", "RETURN": "V-",
    "CAN_GND": "GND", "CANL": "CANL", "CANH": "CANH",
    "VFIELD": "V+", "GND": "GND",
    "+3V3": "3V3", "SWDIO": "DIO", "SWCLK": "CLK", "NRST": "RST",
    "CANH_LEG": "H", "CANL_LEG": "L", "SPLIT": "M",
}
for _channel in range(1, OUTPUT_COUNT + 1):
    CONNECTOR_CONTACT_MARKS["DO%d" % _channel] = "DO%d" % _channel
for _channel in range(1, INPUT_COUNT + 1):
    CONNECTOR_CONTACT_MARKS["DI%d" % _channel] = "DI%d" % _channel


#: What a probe is marked with. Short enough to sit beside its pad without
#: running into the part next to it, and tied to the net it names.
NET_MARKS = {
    INPUT_RAIL_NET: "V24", FIELD_SUPPLY_NET: "VF",
    INTERMEDIATE_RAIL_NET: "5V", LOGIC_RAIL_NET: "3V3",
    GROUND_NET: "GND", "CANH": "CANH", "CANL": "CANL",
    "CAN_TXD": "TXD", "CAN_RXD": "RXD",
}


#: Which pin of each connector carries which function, in pin order.
CONNECTOR_PIN_ORDER = {
    "J1": ("V24_IN", "RETURN"),
    "J2": ("CAN_GND", "CANL", "CANH"),
    "J3": ("VFIELD", "DO1", "DO2", "DO3", "DO4"),
    "J4": ("GND", "DI1", "DI2", "DI3", "DI4"),
    "J5": ("+3V3", "SWDIO", "SWCLK", "NRST", "GND"),
    "J6": ("CANH_LEG", "SPLIT"),
    "J7": ("CANL_LEG", "SPLIT"),
}


def _nets():
    ground = [
        "Q1.2", "D2.2", "C1.2", "C2.2", "U3.2",
        "C4.2", "C5.2", "C6.2", "C7.2", "C8.2", "D3.2", "R3.2", "R5.2",
        "U4.1", "C9.2", "C10.2", "R6.2", "U1.16", "U1.32", "U1.14",
        "C11.2", "C12.2", "C13.2", "C14.2", "C15.2", "Y1.2", "Y1.4",
        "C16.2", "C17.2", "U2.2", "C18.2", "C19.2", "D4.3", "C20.2",
        "R7.2", "R8.2", "D13.1", "TP5.1", "#FLG2.1",
        # the reference the field and bus connectors bring in
        "J2.1", "J4.1", "J5.5",
    ]
    supply_return = ["J1.2", "Q1.3", "D1.1", "#FLG3.1"]
    input_rail = [
        "J1.1", "D1.2", "R1.1", "C1.1", "C2.1", "F1.1", "U3.5", "C4.1",
        "C5.1", "R4.1", "TP1.1", "#FLG1.1",
    ]
    field_supply = ["F1.2", "J3.1", "TP2.1", "#FLG4.1"]
    intermediate_rail = [
        "L1.2", "C6.1", "C7.1", "C8.1", "U4.2", "U2.3", "C18.1", "R2.1",
        "TP3.1", "#FLG5.1",
    ]
    logic_rail = [
        "U4.3", "C9.1", "C10.1", "R6.1", "U1.1", "U1.17", "U1.15",
        "C11.1", "C12.1", "C13.1", "C14.1", "U2.5", "C19.1",
        "J5.1", "TP4.1",
    ]
    for channel in range(1, INPUT_COUNT + 1):
        ground.append("R%d.2" % (channel + 17))
        ground.append("C%d.2" % (channel + 20))
        logic_rail.append("D%d.1" % (channel + 4))
    for channel in range(1, OUTPUT_COUNT + 1):
        ground.append("Q%d.2" % (channel + 1))
        ground.append("R%d.2" % (channel + 29))
        ground.append("D%d.2" % (channel + 8))

    nets = {
        GROUND_NET: ground,
        SUPPLY_RETURN_NET: supply_return,
        INPUT_RAIL_NET: input_rail,
        FIELD_SUPPLY_NET: field_supply,
        INTERMEDIATE_RAIL_NET: intermediate_rail,
        LOGIC_RAIL_NET: logic_rail,
        # reverse-blocking gate, clamped so the rail cannot exceed the
        # device's gate rating
        "BLOCK_G": ["R1.2", "D2.1", "Q1.1"],
        # step-down converter
        "SW_NODE": ["U3.6", "D3.1", "L1.1", "C3.2"],
        "BOOT": ["U3.1", "C3.1"],
        "FB": ["U3.3", "R2.2", "R3.1"],
        "EN": ["U3.4", "R4.2", "R5.1"],
        # controller
        "NRST": ["U1.%s" % RESET_PIN, "C15.1", "J5.4"],
        "XIN": ["U1.%s" % OSC_IN_PIN, "Y1.1", "C16.1"],
        "XOUT": ["U1.%s" % OSC_OUT_PIN, "Y1.3", "C17.1"],
        "BOOT0": ["U1.%s" % BOOT_PIN, "R7.1"],
        "STATUS": ["U1.%s" % STATUS_LED_PIN, "R11.1"],
        "SWDIO": ["U1.%s" % SWDIO_PIN, "R12.1"],
        "SWD_DIO": ["R12.2", "J5.2"],
        "SWCLK": ["U1.%s" % SWCLK_PIN, "R13.1"],
        "SWD_CLK": ["R13.2", "J5.3"],
        "LED_A": ["R11.2", "D13.2"],
        # bus
        "CAN_TXD": ["U1.%s" % CAN_TX_PIN, "U2.1", "TP8.1"],
        "CAN_RXD": ["U1.%s" % CAN_RX_PIN, "U2.4", "TP9.1"],
        "CAN_STB": ["U1.%s" % TRANSCEIVER_STANDBY_PIN, "U2.8", "R8.1"],
        "CANH": ["J2.3", "D4.1", "R9.1", "U2.7", "TP6.1"],
        "CANL": ["J2.2", "D4.2", "R10.1", "U2.6", "TP7.1"],
        "TERM_H": ["R9.2", "J6.1"],
        "TERM_L": ["R10.2", "J7.1"],
        "TERM_SPLIT": ["J6.2", "J7.2", "C20.1"],
    }
    for channel in range(1, INPUT_COUNT + 1):
        terminal = "DI%d" % channel
        nets[terminal] = ["J4.%d" % (channel + 1),
                          "R%d.1" % (channel + 13)]
        nets["DI%d_DIV" % channel] = [
            "R%d.2" % (channel + 13), "R%d.1" % (channel + 17),
            "R%d.1" % (channel + 21), "C%d.1" % (channel + 20),
            "D%d.2" % (channel + 4)]
        nets["DI%d_IN" % channel] = [
            "R%d.2" % (channel + 21),
            "U1.%s" % INPUT_PINS[channel - 1]]
    for channel in range(1, OUTPUT_COUNT + 1):
        nets["DO%d_GATE" % channel] = [
            "R%d.2" % (channel + 25), "R%d.1" % (channel + 29),
            "Q%d.1" % (channel + 1)]
        nets["DO%d_DRV" % channel] = [
            "U1.%s" % OUTPUT_PINS[channel - 1], "R%d.1" % (channel + 25)]
        nets["DO%d" % channel] = [
            "Q%d.3" % (channel + 1), "D%d.1" % (channel + 8),
            "J3.%d" % (channel + 1)]
    return nets


NETS = _nets()

NO_CONNECT = tuple("U1.%s" % pin for pin in MCU_UNUSED_PINS)


#: What the board's silkscreen declares and every rail claim is evaluated
#: over. 24 V nominal; the lower end is what the field supply may sag to and
#: still be inside the declared range, the upper end is what every part
#: behind the terminal is rated above and what the input clamp stands off.
INPUT_SUPPLY = {"min_v": 18.0, "max_v": 30.0}

#: The highest the protected rail can be driven for the length of a transient
#: before anything behind the terminal is outside its rating. It is the input
#: clamp's own clamping voltage at its rated peak pulse current, and it is
#: the number every downstream voltage rating is compared against.
TRANSIENT_CLAMP_MAX_V = 48.4

#: Per-channel field output current the board is rated for, with all four
#: channels conducting at once.
OUTPUT_CURRENT_RATING_A = 0.25

#: The highest ambient the board's ratings are claimed at. The resettable
#: fuse's hold current and the controller's supply current are both read from
#: their datasheets at or above this temperature.
AMBIENT_MAX_C = 60.0

RAILS = {
    INPUT_RAIL_NET: dict(INPUT_SUPPLY),
    FIELD_SUPPLY_NET: dict(INPUT_SUPPLY),
    GROUND_NET: {"min_v": 0.0, "max_v": 0.0},
    SUPPLY_RETURN_NET: {"min_v": 0.0, "max_v": 0.0},
}

#: Every net the board treats as a supply.
POWER_NETS = tuple(RAILS) + (INTERMEDIATE_RAIL_NET, LOGIC_RAIL_NET)

#: The highest prospective fault current the installation may present at the
#: board's terminals. Not a property of this board: the supply's own current
#: limit and the field wiring set it. The resettable fuse cannot be shown to
#: survive more than its own maximum fault current, so the board declares the
#: figure the installation has to respect rather than assuming a wiring
#: resistance that would make the question go away.
SUPPLY_PROSPECTIVE_FAULT_CURRENT_MAX_A = 30.0

#: A budget, not a measurement: board copper between the input terminal and a
#: field output pin, before layout exists to measure it.
BOARD_COPPER_BUDGET_OHM = 0.03

#: Bus rate the node is qualified for. The arbitration rate is the classical
#: CAN ceiling; the data-phase rate is the one the transceiver's datasheet
#: characterises for its "G" variants, which is the part fitted here.
ARBITRATION_RATE_BPS = 1.0e6
DATA_PHASE_RATE_BPS = 5.0e6

#: Nominal differential termination the bus expects, and what this board
#: presents when both of its links are fitted: two equal legs about a
#: filtered centre point, which is the load the transceiver's own datasheet
#: characterises its outputs into. Each leg carries its own link, one on
#: each side of the bus pair, so pulling both removes the differential load
#: rather than leaving one line loaded against the centre capacitor - and
#: neither leg has to cross the pair to reach the other, which is what puts
#: the two links on opposite sides instead of in one header.
TERMINATION_NOMINAL_OHM = 120.0
TERMINATION_LEG_OHM = 60.4

#: The link that closes a termination leg. It is not soldered to the board,
#: so it is not on the assembly BOM; it is fitted by hand and is what the
#: termination claims are evaluated against.
TERMINATION_LINK = {
    "mpn": "2.54Short Circuit Cap Closed",
    "lcsc": "C100114",
    "manufacturer": "BOOMELE(Boom Precision Elec)",
    "count": 2,
}

#: Discharge level the bus terminals are claimed to withstand, and the test
#: it is claimed under.
ESD_CONTACT_LEVEL_V = 8000.0
ESD_STANDARD = "IEC 61000-4-2 contact discharge, powered"

#: Oscillator tolerance the node's bit timing is evaluated against. A design
#: target derived from the classical requirement that two nodes' clocks must
#: not drift more than a fraction of a bit over the longest unsynchronised
#: stretch; each node is given half of it.
OSCILLATOR_TOLERANCE_BUDGET_PPM = 5000.0

#: A budget, not a measurement: everything on the bus beyond this board's own
#: connector - the cable and the far end - as one capacitance on each
#: conductor. It is what the bus-edge scenario loads the driver with.
BUS_CABLE_CAPACITANCE_BUDGET_F = 100.0e-12

#: How much of a data-phase bit the bus is allowed to spend settling, and how
#: close to its settled level it must be by then. Design targets, not
#: standard figures.
BUS_SETTLING_FRACTION_OF_BIT = 1.0
BUS_SETTLED_FRACTION = 0.9

#: The longest a field input may take to reach the receiver's threshold after
#: its terminal changes. A design target: the filter that gives the input its
#: noise immunity is what sets it.
INPUT_RESPONSE_TIME_S = 1.0e-3

#: Stray capacitance the crystal's load network is sized with, per pin. The
#: controller datasheet offers 10 pF as a rough estimate of the combined pin
#: and board capacitance, which is 5 pF at each of the two pins.
CRYSTAL_STRAY_CAPACITANCE_F = 5.0e-12

#: Nets that must reach a probe with the board installed, from the brief's
#: bring-up requirement: every rail, both bus conductors, and the pair the
#: transceiver exchanges with the controller.
PROBE_REQUIRED_NETS = (
    INPUT_RAIL_NET, FIELD_SUPPLY_NET, INTERMEDIATE_RAIL_NET,
    LOGIC_RAIL_NET, GROUND_NET, "CANH", "CANL", "CAN_TXD", "CAN_RXD")

#: The build this board is costed and supplied for.
PLANNED_BUILD_QUANTITY = 50

#: What the assembler has to do beyond one reflow of the front side.
ASSEMBLY_POLICY = {
    "placement_sides": 1,
    # four field terminal blocks, the programming header and the two
    # termination-link headers
    "through_hole_soldered_parts": 7,
    # the two termination links, which push on rather than solder
    "hand_fitted_parts": TERMINATION_LINK["count"],
}

#: A conductor that leaves the board and needs no clamp of its own, and why.
PROTECTION_EXEMPT = {
    GROUND_NET: "the reference every clamp on this board diverts into",
    SUPPLY_RETURN_NET: "the return terminal, clamped to the input terminal "
                       "by the bidirectional input suppressor and blocked "
                       "from the reference by the reverse-blocking device",
    LOGIC_RAIL_NET: "reaches the programming header only, which is a "
                    "service interface used with the enclosure open and is "
                    "not field wiring",
    "SWD_DIO": "programming header, as above",
    "SWD_CLK": "programming header, as above",
    "NRST": "programming header, as above",
    FIELD_SUPPLY_NET: "the field output supply, taken from the input rail "
                      "behind the input suppressor and the resettable fuse",
}
for _channel in range(1, INPUT_COUNT + 1):
    PROTECTION_EXEMPT["DI%d" % _channel] = (
        "survives the declared input range in either polarity by its own "
        "series network rather than by a clamp at the terminal")


#: Connectors that carry conductors in from outside the board. The
#: termination links are not among them: both ends of every one of their
#: pins are copper on this board, so nothing arrives through them and there
#: is nothing at them to protect against.
EXTERNAL_CONNECTORS = ("J1", "J2", "J3", "J4", "J5")


def entering_conductors():
    """Every conductor that enters the board, and the connector it enters by.

    Each one either carries a clamp of its own or appears in
    PROTECTION_EXEMPT with a reason.
    """
    entering = {}
    for reference in EXTERNAL_CONNECTORS:
        for net in CONNECTOR_FUNCTION_NETS[reference].values():
            entering.setdefault(net, []).append(reference)
    return {net: sorted(refs) for net, refs in entering.items()}


def pin_to_net():
    mapping = {}
    for net_name, pin_refs in NETS.items():
        for pin_ref in pin_refs:
            if pin_ref in mapping:
                raise ValueError(
                    "pin %s assigned to both %s and %s"
                    % (pin_ref, mapping[pin_ref], net_name))
            mapping[pin_ref] = net_name
    for pin_ref in NO_CONNECT:
        if pin_ref in mapping:
            raise ValueError(
                "pin %s is both no-connect and on net %s"
                % (pin_ref, mapping[pin_ref]))
    return mapping
