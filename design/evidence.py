from __future__ import annotations

import hashlib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(REPO_ROOT, "evidence", "index.json")
DATASHEET_DIR = os.path.join(REPO_ROOT, "evidence", "datasheets")

#: Every document a claim in this repository rests on. `url` is where the file
#: came from; `document_id` is the revision the file itself states, which is
#: what a later reader has to match to know they are reading the same thing.
SOURCES = {
    "stm32g431_st": {
        "file": "datasheets/stm32g431_st.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "3f23d741047d660d2a0e8aabbc953854.pdf",
        "retrieved": "2026-09-02",
        "document_id": "STM32G431x6/x8/xB datasheet DS12589 Rev 2, "
                       "October 2019",
        "applies_to": ["STM32G431KBT6"],
    },
    "tcan1042_ti": {
        "file": "datasheets/tcan1042_ti.pdf",
        "url": "https://www.ti.com/lit/ds/symlink/tcan1042h.pdf",
        "retrieved": "2026-09-02",
        "document_id": "TCAN1042H/HG/HGV/HV, SLLSES7D, March 2016, revised "
                       "October 2021",
        "applies_to": ["TCAN1042HGVDR"],
    },
    "mp2459_mps": {
        "file": "datasheets/mp2459_mps.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2304140030_Monolithic-Power-Systems-MP2459GJ-Z_C39578.pdf",
        "retrieved": "2026-09-02",
        "document_id": "MP2459 0.5A 55V 480kHz step-down converter, "
                       "Rev. 1.1, 2021-05-21",
        "applies_to": ["MP2459GJ-Z"],
    },
    "ht75rxx_holtek": {
        "file": "datasheets/ht75rxx_holtek.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "59abfa7ca0c1b0cd081d8e8f60c28ed0.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Holtek HT75Rxx-1 30V 150mA LDO, Rev. 1.01, "
                       "2025-12-03",
        "applies_to": ["HT75R33-1A"],
    },
    "nce6003x_nce": {
        "file": "datasheets/nce6003x_nce.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2201121630_Wuxi-NCE-Power-Semiconductor-NCE6003X_"
               "C2934580.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Wuxi NCE Power NCE6003X 60V 3A N-channel MOSFET",
        "applies_to": ["NCE6003X"],
    },
    "wst6066a_winsok": {
        "file": "datasheets/wst6066a_winsok.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "fa81b0d9ae88480fa681d4eacf953c2b.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Winsok WST6066A 60V N-channel MOSFET",
        "applies_to": ["WST6066A"],
    },
    "smaj_mdd": {
        "file": "datasheets/smaj_mdd.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "57d80c866df506764ddd60be335ccdff.pdf",
        "retrieved": "2026-09-02",
        "document_id": "MDD SMAJ5.0(C)A through SMAJ440(C)A, 400 W "
                       "transient voltage suppressor",
        "applies_to": ["SMAJ30CA"],
    },
    "smf_jingdao": {
        "file": "datasheets/smf_jingdao.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "e2079ce6902d97aebf17ffdc9542d2e7.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Jingdao SMF series 200 W SOD-123FL transient "
                       "voltage suppressor",
        "applies_to": ["SMF30A"],
    },
    "bzt52c12_mdd": {
        "file": "datasheets/bzt52c12_mdd.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "61190d79e0f948958471ae8476bcd111.pdf",
        "retrieved": "2026-09-02",
        "document_id": "MDD BZT52 series 500 mW zener diodes",
        "applies_to": ["BZT52C12"],
    },
    "b1100_diodes": {
        "file": "datasheets/b1100_diodes.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "53f31132fb725db38e9b9ec760d65c73.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Diodes Incorporated B170/B - B1100/B, "
                       "DS30018 Rev. 15-2, June 2022",
        "applies_to": ["B1100-13-F"],
    },
    "esdcan05_st": {
        "file": "datasheets/esdcan05_st.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2304140030_STMicroelectronics-ESDCAN05-2BWY_C1973137.pdf",
        "retrieved": "2026-09-02",
        "document_id": "ESDCANxx-2BWY datasheet DS12789 Rev 2, "
                       "November 2018",
        "applies_to": ["ESDCAN05-2BWY"],
    },
    "1n4148w_semtech": {
        "file": "datasheets/1n4148w_semtech.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "8abd7fc00ebe41ffb03ad1383c10753b.pdf",
        "retrieved": "2026-09-02",
        "document_id": "1N4148W SOD-123 switching diode",
        "applies_to": ["1N4148W"],
    },
    "kt0603r_kento": {
        "file": "datasheets/kt0603r_kento.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "011ec3e8cb1e825f6961d29bc4db4c7a.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Hubei KENTO KT-0603R specification",
        "applies_to": ["KT-0603R"],
    },
    "ind_swpa5040_sunlord": {
        "file": "datasheets/ind_swpa5040_sunlord.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2310251551_Sunlord-SWPA5040S470MT_C86617.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Sunlord SWPA series wire wound SMD power "
                       "inductors, revised 2023/06/01",
        "applies_to": ["SWPA5040S470MT"],
    },
    "xtal_8mhz_yxc": {
        "file": "datasheets/xtal_8mhz_yxc.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2403291503_YXC-Crystal-Oscillators-XL1EL89CMI-111YLC-8M_"
               "C19711736.pdf",
        "retrieved": "2026-09-02",
        "document_id": "YXC YSX531SL crystal unit specification",
        "applies_to": ["XL1EL89CMI-111YLC-8M"],
    },
    "pptc_1812l200_lute": {
        "file": "datasheets/pptc_1812l200_lute.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2309271034_LUTE-1812L200-33GR_C18198343.pdf",
        "retrieved": "2026-09-02",
        "document_id": "LUTE 1812L series surface mount resettable fuses, "
                       "Revision 2020",
        "applies_to": ["1812L200/33GR"],
    },
    "header1x2_kinghelm": {
        "file": "datasheets/header1x2_kinghelm.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2110191530_Shenzhen-Kinghelm-Elec-KH-2-54PH180-1X2P-L11-5_"
               "C2905434.pdf",
        "retrieved": "2026-09-02",
        "applies_to": ["KH-2.54PH180-1X2P-L11.5"],
    },
    "jumper_shunt_boomele": {
        "file": "datasheets/jumper_shunt_boomele.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2303231100_BOOMELE-Boom-Precision-Elec-2-54_C100114.pdf",
        "retrieved": "2026-09-02",
        "document_id": "BOOMELE 2.54 mm closed short-circuit cap drawing",
        "applies_to": ["2.54Short Circuit Cap Closed"],
    },
    "term_db128v_dorabo": {
        "file": "datasheets/term_db128v_dorabo.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2301061509_DORABO-DB128V-5-08-2P-GN-S_C2915639.pdf",
        "retrieved": "2026-09-02",
        "document_id": "DORABO DB128V-5.08-XXP-C-S customer drawing, "
                       "rev T0-1, 2022-10-27",
        "applies_to": ["DB128V-5.08-2P-GN-S", "DB128V-5.08-3P-GN-S",
                       "DB128V-5.08-5P-GN-S"],
    },
    "header1x5_kinghelm": {
        "file": "datasheets/header1x5_kinghelm.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2201121530_Shenzhen-Kinghelm-Elec-KH-2-54PH180-1X5P-L11-5_"
               "C2932699.pdf",
        "retrieved": "2026-09-02",
        "applies_to": ["KH-2.54PH180-1X5P-L11.5"],
    },
    "res_uniroyal": {
        "file": "datasheets/res_uniroyal.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "0a975aaa49b7c97f38a963127be4a823.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Uniroyal chip resistor series specification",
        "applies_to": ["0603WAF1000T5E", "0603WAF4700T5E",
                       "0603WAF2701T5E", "0603WAF1002T5E",
                       "0603WAF2002T5E", "0603WAF2372T5E",
                       "0603WAF5102T5E", "0603WAF1003T5E",
                       "0603WAF1243T5E", "0603WAF4703T5E",
                       "0603WAF5602T5E"],
    },
    "res_rmcf_stackpole": {
        "file": "datasheets/res_rmcf_stackpole.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "cc8d4427ec8b6553eb327eea67662c30.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Stackpole RMCF/RMCP series thick film chip "
                       "resistors",
        "applies_to": ["RMCF2512FT60R4"],
    },
    "mlcc_yageo_cc": {
        "file": "datasheets/mlcc_yageo_cc.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "23ccee80ee542e7cf156a772bb589942.pdf",
        "retrieved": "2026-09-02",
        "document_id": "YAGEO CC series multilayer ceramic capacitor "
                       "specification",
        "applies_to": ["CC0603JRNPO9BN150", "CC0603KRX7R0BB472",
                       "CC0603KRX7R0BB103", "CC0603KRX7R0BB104",
                       "CC0603KRX7R8BB105", "CC0805KKX7R7BB106",
                       "CC1206KKX7R0BB105"],
    },
    "elcap_rvt_jieerrui": {
        "file": "datasheets/elcap_rvt_jieerrui.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "b62932148c4d9d6f60e49356f14710e8.pdf",
        "retrieved": "2026-09-02",
        "document_id": "RVT series SMD aluminium electrolytic capacitor "
                       "specification",
        "applies_to": ["RVT63V47M6X8"],
    },
}


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_index():
    entries = {}
    for name in sorted(SOURCES):
        source = SOURCES[name]
        path = os.path.join(REPO_ROOT, "evidence", source["file"])
        entry = dict(source)
        entry["sha256"] = digest(path)
        entry["bytes"] = os.path.getsize(path)
        entries[name] = entry
    return {"schema_version": 1, "documents": entries}


def load_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_index():
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(compute_index(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return INDEX_PATH


def verify():
    """Every recorded document present and unchanged, and nothing unrecorded."""
    recorded = load_index()["documents"]
    present = {name for name in os.listdir(DATASHEET_DIR)
               if name.endswith((".pdf", ".json"))}
    referenced = {os.path.basename(entry["file"])
                  for entry in recorded.values()}
    problems = []
    for name in sorted(referenced - present):
        problems.append(("missing_file", name))
    for name in sorted(present - referenced):
        problems.append(("unreferenced_file", name))
    for name in sorted(recorded):
        entry = recorded[name]
        path = os.path.join(REPO_ROOT, "evidence", entry["file"])
        if not os.path.isfile(path):
            continue
        if digest(path) != entry["sha256"]:
            problems.append(("digest_mismatch", name))
    return problems


if __name__ == "__main__":
    sys.stdout.write(write_index() + "\n")
