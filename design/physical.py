"""The board's physical inputs, taken from documents rather than assumed.

Two numbers decide what a length of copper on this board actually is: how
thick the conductor is and how thick the board under it is. Neither is a
choice this design gets to make - the first is the fabricator's own stated
finished thickness for the copper weight ordered, the second is the
thickness the fabrication requirements declare - and both are carried with
the digest of the document they came from, so a later reader can tell an
approved figure from a number somebody typed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
REQUIREMENTS_PATH = os.path.join(REPO_ROOT, "fab", "requirements.json")
SELECTION_PATH = os.path.join(REPO_ROOT, "fab", "selection.json")
PHYSICAL_PATH = os.path.join(REPO_ROOT, "fab", "physical_inputs.json")

if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa import extract  # noqa: E402
from pcbqa.fabricators import store  # noqa: E402

PROFILE_ROOT = os.path.join(TOOLKIT_ROOT, "profiles", "jlcpcb")

#: The board's copper layers, front to back. Two layers, both external,
#: which is why no inner copper weight is declared anywhere.
COPPER_LAYER_STACK = ("F.Cu", "B.Cu")


def load_requirements():
    with open(REQUIREMENTS_PATH, "rb") as handle:
        body = handle.read()
    return json.loads(body.decode("utf-8")), hashlib.sha256(body).hexdigest()


def approved_snapshot():
    """The fabricator catalogue this board was judged feasible against.

    The selection recorded which snapshot it read; if the catalogue has
    moved on since, the physical inputs would silently come from a
    different document than the feasibility did, so that is refused
    rather than reconciled.
    """
    snapshot = store.CatalogStore(PROFILE_ROOT).approved()
    if snapshot is None:
        raise RuntimeError("no approved fabricator catalogue at "
                           + PROFILE_ROOT)
    with open(SELECTION_PATH, "r", encoding="utf-8") as handle:
        selection = json.load(handle)
    if selection["approved_normalized_sha256"] != \
            snapshot["normalized_sha256"]:
        raise RuntimeError(
            "the fabricator catalogue has changed since the process "
            "selection was frozen (%s -> %s); re-run the selection rather "
            "than mixing the two"
            % (selection["approved_normalized_sha256"][:12],
               snapshot["normalized_sha256"][:12]))
    return snapshot


def document():
    requirements, digest = load_requirements()
    assignments = extract.copper_assignments_from_requirements(
        requirements, list(COPPER_LAYER_STACK))
    return {
        "board_thickness_mm": extract.requirements_board_thickness(
            requirements, digest),
        "copper_thickness_mm": extract.approved_finished_copper(
            approved_snapshot(), assignments),
    }


def write():
    with open(PHYSICAL_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return PHYSICAL_PATH


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
