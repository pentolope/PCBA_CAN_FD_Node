"""Routing: the toolkit runs the search this board declares.

The candidate loop that lived here - stage the placed board, invoke the
router, tidy, judge, record, adopt or restore - is the toolkit's owned
search now. The board keeps only the declaration, in
`board/manifest.json` under `routing.search` and `routing.transforms`,
and the one step only this repository can take: regenerating the placed
board from the design source before the search runs over it.
"""
from __future__ import annotations

import os
import subprocess
import sys

from . import layout


def run():
    layout.write()
    proc = subprocess.run(
        [sys.executable,
         os.path.join("tooling", "PCBA_AutoDesignAndTest", "run.py"),
         "route", os.path.join("board", "manifest.json"), "--adopt"],
        cwd=layout.REPO_ROOT, check=False)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    run()
