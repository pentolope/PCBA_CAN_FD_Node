"""Routing: the search draws ordinary connectivity, nothing else.

Four nets are withheld from it. The two grounds are pours with a via at every
surface pad, and which ground a pad joins is a property of its net rather
than of a search. The protected rail and the input are pours too, because the
whole board's current runs through them and a track wide enough to carry it
is a pour by another name. What is left is signal connectivity, and that is
what the router is for.

A candidate is judged, not trusted: it is adopted, the board is measured, and
if it does not come back clean the placed board is restored so no failing
copper stays in the tree.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys

import pcbnew

from . import build, layout, netlist

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tooling", "PCBA_AutoDesignAndTest"))

from pcbqa import routing_record  # noqa: E402

REPO_ROOT = layout.REPO_ROOT
CANDIDATE_ROOT = os.path.join(REPO_ROOT, "candidates")
CANDIDATE_NAME = "route-current"
PROVENANCE_PATH = os.path.join(REPO_ROOT, "generated", "routing.json")

#: Nets the search may not draw, and the copper that already carries them.
#: The reference is a pour with a via at every surface pad, and which
#: reference a pad joins is a property of its net rather than of a search.
#: The input rail and the field supply are pours too, because the whole
#: board's current runs through them. The bus pair, the field outputs and
#: the termination's centre are drawn because their topology is a
#: requirement: constant spacing over an unbroken return, one conductor per
#: channel, and a centre node that crosses neither bus conductor. So is the
#: converter's switch node, whose enclosed area is what its edges radiate
#: from.
RESERVED_NETS = ((netlist.GROUND_NET, netlist.INPUT_RAIL_NET,
                  netlist.FIELD_SUPPLY_NET, netlist.SUPPLY_RETURN_NET,
                  "CANH", "CANL", "TERM_SPLIT", "SW_NODE")
                 + tuple("DO%d" % channel
                         for channel in range(1, netlist.OUTPUT_COUNT + 1)))


def routed_nets():
    return tuple(sorted(name for name in netlist.NETS
                        if name not in RESERVED_NETS))


#: The router is given a wider clearance than the rule the board is judged by.
#: It takes the figure from the project's Default net class, and its diagonal
#: segments then land short of it, so the candidate is routed against a
#: project carrying this margin and judged against the authoritative one,
#: which `_adopt` restores.
ROUTER_CLEARANCE_MM = 0.30

ROUTER_OPTIONS = (
    "--track-width", str(layout.TRACK_WIDTH_MM),
    "--clearance", str(ROUTER_CLEARANCE_MM),
    "--via-size", str(layout.VIA_DIAMETER_MM),
    "--via-drill", str(layout.VIA_DRILL_MM),
    "--board-edge-clearance", "0.45",
    "--hole-to-hole-clearance", "0.3",
    "--same-net-pad-clearance", "0.3",
    "--no-power-tap-neckdown",
    # The copper this design draws itself is drawn because its geometry is a
    # requirement. Without this the router treats it as its own previous
    # output: it rips it up, reroutes it wherever the search prefers, and
    # the requirement is gone. Here it is an obstacle like any other.
    "--keep-input-copper",
)

# The router is deterministic for a fixed input, so a bare retry explores
# nothing. Each attempt varies the net-ordering strategy instead, which is
# what actually produces a different candidate.
#: The search is repeated over the same orderings because the router is not
#: deterministic: the same board and the same ordering can come back with a
#: different set of vias, and a candidate carrying one sub-clearance item is
#: rejected rather than patched. Each repeat is a distinct candidate, and
#: every one of them is recorded whether it was accepted or not.
ATTEMPT_ORDERINGS = ("inside_out", "original", "mps") * 3
MAX_ATTEMPTS = len(ATTEMPT_ORDERINGS)

#: A track end is pulled onto a via's centre only when it already stands on
#: that via's own copper. A larger reach would move copper the clearance
#: check has already accepted; this one cannot, because the destination is
#: inside the annulus the end is already touching.
SNAP_WITHIN_VIA = True
#: The shortest track fragment the board accepts away from a pad or a via.
#: A router turning a diagonal lands it as a staircase of pieces far below
#: this; each one is a manufacturing risk rather than a connection, so the
#: pieces are collapsed into their neighbours.
MIN_SEGMENT_MM = 0.1
TOUCH_TOLERANCE_MM = 0.01


def _krt():
    from pcbqa import krt
    return krt


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _summary(text):
    for line in text.splitlines():
        if line.strip().startswith("JSON_SUMMARY_MIN:"):
            return json.loads(line.split("JSON_SUMMARY_MIN:", 1)[1])
    return {}


def _write_routing_project(path):
    """The project the router sees: the design's, with the clearance margin."""
    document = build.project_document(
        str(build.schematic._uuid("sheet", netlist.PROJECT_NAME)))
    document["board"]["design_settings"]["rules"]["min_clearance"] = \
        ROUTER_CLEARANCE_MM
    for entry in document["net_settings"]["classes"]:
        if entry["name"] == "Default":
            entry["clearance"] = ROUTER_CLEARANCE_MM
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    return path


#: The router carries its own fab-capability floor and is free to escalate
#: below the nominal clearance to fit tight geometry, recording the tighter
#: value so the board is graded against it. This board is graded against its
#: own declared constraints instead, so the router is given those constraints
#: as its floor: copper it emits is then legal by the same rule the checker
#: applies, rather than legal only against a floor the router lowered.
def _write_fab_floor(path):
    floors = (("clearance", build.DESIGN_RULES["min_clearance"]),
              ("track_width", build.DESIGN_RULES["min_track_width"]),
              ("via_diameter", layout.VIA_DIAMETER_MM),
              ("via_drill", layout.VIA_DRILL_MM),
              ("hole_to_hole", build.DESIGN_RULES["min_hole_to_hole"]),
              ("board_edge", build.DESIGN_RULES["min_copper_edge_clearance"]))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# generated from the board's declared constraints\n")
        for key, value in floors:
            handle.write("%s = %s\n" % (key, value))
    return path


def _route_once(resolved, candidate, attempt, placed_pcb):
    stage_dir = os.path.join(candidate, "attempt-%02d" % attempt)
    os.makedirs(stage_dir, exist_ok=True)
    source_pcb = os.path.join(stage_dir, "source.kicad_pcb")
    shutil.copy(placed_pcb, source_pcb)
    _write_routing_project(os.path.join(stage_dir, "source.kicad_pro"))
    routed_pcb = os.path.join(stage_dir, "routed.kicad_pcb")
    floor = _write_fab_floor(os.path.join(stage_dir, "fab-floor.txt"))
    command = [sys.executable,
               os.path.join(resolved["path"], "py_router", "route.py"),
               source_pcb, "--output", routed_pcb, "--nets"] \
        + list(routed_nets()) + list(ROUTER_OPTIONS) \
        + ["--fab-overrides", floor,
           "--ordering", ATTEMPT_ORDERINGS[attempt - 1]]
    completed = subprocess.run(command, capture_output=True, text=True)
    summary = _summary(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError("routing failed: rc=%s summary=%s stderr=%s"
                           % (completed.returncode, summary,
                              completed.stderr[-2000:]))
    tidied_pcb = os.path.join(stage_dir, "tidied.kicad_pcb")
    shutil.copy(routed_pcb, tidied_pcb)
    transform = tidy(tidied_pcb)
    return {
        "attempt": attempt,
        "source_sha256": digest(source_pcb),
        "accepted": False,
        "stages": [
            {"stage": "routed", "produced_by": "router",
             "sha256": digest(routed_pcb)},
            {"stage": "tidied", "produced_by": "transform",
             "sha256": digest(tidied_pcb),
             "transform": "snap a track end standing on a same-net via onto that via's centre; "
                          "pull a track end whose own copper overlaps a "
                          "same-net pad onto that pad's anchor; "
                          "drop tracks the snap collapsed to a point; "
                          "split a track where another track's end stands on "
                          "it, so the junction is one the checker can see; "
                          "drop a track that duplicates another exactly; "
                          "restore the declared width on any track and the "
                          "declared size on any via the search narrowed "
                          "below them; prune dangling track ends, "
                          "keeping any removal only while connectivity is "
                          "unchanged; refill the zones so the pours are "
                          "knocked out around the copper the router added",
             "effects": transform,
             "parameters": {"snap_within_via_annulus": SNAP_WITHIN_VIA,
                            "touch_tolerance_mm": TOUCH_TOLERANCE_MM}},
        ],
        "context": {"router_summary": summary,
                    "ordering": ATTEMPT_ORDERINGS[attempt - 1]},
        "board": tidied_pcb,
    }


def measure(path):
    """What the board says about itself: violations, and what is still open."""
    report = os.path.join(CANDIDATE_ROOT, CANDIDATE_NAME, "adopted-drc.json")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    completed = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--output", report, "--format", "json",
         "--severity-error", "--severity-warning", path],
        capture_output=True, text=True)
    if completed.returncode != 0 and not os.path.isfile(report):
        raise RuntimeError("DRC did not run: " + completed.stderr[-2000:])
    with open(report, encoding="utf-8") as handle:
        document = json.load(handle)
    counted = document.get("violations") or []
    return {
        "errors": sum(1 for entry in counted
                      if entry.get("severity") == "error"),
        "warnings": sum(1 for entry in counted
                        if entry.get("severity") != "error"),
        "unconnected": len(document.get("unconnected_items") or []),
        "schematic_parity": len(document.get("schematic_parity") or []),
    }


def _accepts(metrics):
    """What a candidate has to be before it replaces the board in the tree.

    Everything the board's own severities call a finding, because the gate
    that judges the routed board counts warnings too: a candidate that leaves
    one is a candidate the release would reject.
    """
    return (metrics["errors"] == 0 and metrics["warnings"] == 0
            and metrics["unconnected"] == 0
            and metrics["schematic_parity"] == 0)


def _write_record(placed_pcb, attempts, accepted, krt, resolved):
    record = {
        "kind": routing_record.KIND,
        "source_sha256": digest(placed_pcb),
        "attempts": attempts,
        "accepted_attempt": accepted["attempt"] if accepted else None,
        "adopted_sha256": (digest(layout.BOARD_PATH) if accepted else None),
        "context": {
            "router": krt.provenance(resolved["path"], sys.executable),
            "resolution": resolved,
            "routed_nets": list(routed_nets()),
            "reserved_nets": list(RESERVED_NETS),
            "options": list(ROUTER_OPTIONS),
            "acceptance": "a candidate is adopted only when a fresh DRC over "
                          "the adopted board reports no violation, nothing "
                          "unconnected and no disagreement with the "
                          "schematic",
            "reproducibility": "the router is not bit-reproducible; "
                               "candidates are generated until one is "
                               "accepted and every attempt is recorded here",
        },
    }
    routing_record.validate(record)
    os.makedirs(os.path.dirname(PROVENANCE_PATH), exist_ok=True)
    with open(PROVENANCE_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return record


def _adopt(candidate_board):
    """Install a candidate, then rewrite everything derived from the board.

    The router writes its own project file beside the candidate - loosening a
    track width, pinning an edge clearance, silencing severities - so the
    authoritative project is regenerated from the design source rather than
    inherited from whatever the search left behind.
    """
    shutil.copy(candidate_board, layout.BOARD_PATH)
    build.write_project()


def run():
    krt = _krt()
    resolved = krt.resolve()
    candidate = os.path.join(CANDIDATE_ROOT, CANDIDATE_NAME)
    shutil.rmtree(candidate, ignore_errors=True)
    os.makedirs(candidate, exist_ok=True)
    layout.write()
    placed_pcb = os.path.join(candidate, "placed.kicad_pcb")
    shutil.copy(layout.BOARD_PATH, placed_pcb)

    attempts = []
    accepted = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = _route_once(resolved, candidate, attempt, placed_pcb)
        entry = {key: value for key, value in result.items() if key != "board"}
        _adopt(result["board"])
        metrics = measure(layout.BOARD_PATH)
        entry["context"]["adopted_metrics"] = metrics
        entry["accepted"] = _accepts(metrics)
        _write_record(placed_pcb, attempts + [entry],
                      entry if entry["accepted"] else None, krt, resolved)
        attempts.append(entry)
        if entry["accepted"]:
            accepted = entry
            break

    if accepted is None:
        _adopt(placed_pcb)
        _write_record(placed_pcb, attempts, None, krt, resolved)
        raise RuntimeError(
            "no routing candidate was accepted in %d attempts; the placed, "
            "unrouted board has been restored so no failing copper stays in "
            "the tree" % MAX_ATTEMPTS)
    return layout.BOARD_PATH, PROVENANCE_PATH


def _endpoints(track):
    return (track.GetStart(), track.GetEnd())


def _supported(point, track, board, vias, tracks, epsilon):
    for via in vias:
        if via.GetNetCode() != track.GetNetCode():
            continue
        if not via.IsOnLayer(track.GetLayer()):
            continue
        centre = via.GetPosition()
        if math.hypot(point.x - centre.x, point.y - centre.y) <= epsilon:
            return True
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetCode() != track.GetNetCode():
                continue
            # A pad only holds a track end up on a layer it is actually on:
            # an SMD pad on the far side is not a connection, and treating it
            # as one used to leave the end dangling for the checker to find.
            if not pad.IsOnLayer(track.GetLayer()):
                continue
            if pad.HitTest(point, 0):
                return True
    for other in tracks:
        if other.m_Uuid.AsString() == track.m_Uuid.AsString():
            continue
        if other.GetNetCode() != track.GetNetCode():
            continue
        if other.Type() == pcbnew.PCB_VIA_T:
            continue
        if other.GetLayer() != track.GetLayer():
            continue
        if other.HitTest(point, int(epsilon)):
            return True
    return False


def _point_to_segment(point, start, finish):
    """Distance from a point to a segment, and where along it that lands."""
    dx = finish.x - start.x
    dy = finish.y - start.y
    if dx == 0 and dy == 0:
        return math.hypot(point.x - start.x, point.y - start.y), 0.0
    fraction = (((point.x - start.x) * dx + (point.y - start.y) * dy)
                / float(dx * dx + dy * dy))
    fraction = max(0.0, min(1.0, fraction))
    return (math.hypot(point.x - (start.x + fraction * dx),
                       point.y - (start.y + fraction * dy)), fraction)


def _entry_geometry(track, board, vias):
    """True when an end of the track sits on a via or in a pad: copper that
    short is how a route enters one, not a route in its own right."""
    for point in _endpoints(track):
        for via in vias:
            centre = via.GetPosition()
            if math.hypot(point.x - centre.x, point.y - centre.y) \
                    <= via.GetWidth(pcbnew.F_Cu) / 2:
                return True
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.IsOnLayer(track.GetLayer()) and pad.HitTest(point, 0):
                    return True
    return False


def _absorption(fragment, board, vias, tracks, epsilon):
    """The one neighbour a fragment can be folded into, or None.

    A fold is only offered where exactly one same-net track on the same layer
    meets the fragment at that end and no via or pad stands there, so a
    junction and a terminal are both left alone."""
    for point, other in ((fragment.GetStart(), fragment.GetEnd()),
                         (fragment.GetEnd(), fragment.GetStart())):
        for via in vias:
            centre = via.GetPosition()
            if math.hypot(point.x - centre.x, point.y - centre.y) <= epsilon:
                break
        else:
            touching = []
            for candidate in tracks:
                if candidate.m_Uuid.AsString() == fragment.m_Uuid.AsString():
                    continue
                if candidate.GetNetCode() != fragment.GetNetCode():
                    continue
                if candidate.GetLayer() != fragment.GetLayer():
                    continue
                for get, set_ in ((candidate.GetStart, candidate.SetStart),
                                  (candidate.GetEnd, candidate.SetEnd)):
                    end = get()
                    if math.hypot(end.x - point.x, end.y - point.y) <= epsilon:
                        touching.append((candidate, set_, end))
            if len(touching) == 1:
                candidate, set_, end = touching[0]
                return (fragment, candidate, set_, end, other)
    return None


def tidy(path):
    board = pcbnew.LoadBoard(path)
    epsilon = pcbnew.FromMM(TOUCH_TOLERANCE_MM)
    snapped = 0
    for _ in range(4):
        vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        moved = 0
        for track in board.GetTracks():
            if track.Type() == pcbnew.PCB_VIA_T:
                continue
            for get, set_ in ((track.GetStart, track.SetStart),
                              (track.GetEnd, track.SetEnd)):
                point = get()
                for via in vias:
                    if via.GetNetCode() != track.GetNetCode():
                        continue
                    centre = via.GetPosition()
                    distance = math.hypot(point.x - centre.x,
                                          point.y - centre.y)
                    if epsilon < distance <= via.GetWidth(pcbnew.F_Cu) / 2:
                        set_(centre)
                        moved += 1
                        break
        snapped += moved
        if not moved:
            break

    # A track end that stops on a pad's own copper but not on the point the
    # pad is anchored at - inside the outline but outside the shape a rounded
    # rectangle presents, or short of the outline by less than the width of
    # the track itself - reads as connected to the board's connectivity, which
    # asks whether the copper overlaps, and as a bare end to anything that
    # asks what touches the end point. It is pulled to the pad anchor, which
    # is the one point on a pad every reader agrees is on it. The end only
    # ever moves onto copper the pad already holds, so the copper the board
    # carries afterwards is a subset of what it carried before.
    pad_snapped = 0
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        tracks = [t for t in board.GetTracks()
                  if t.Type() != pcbnew.PCB_VIA_T]
        for get, set_ in ((track.GetStart, track.SetStart),
                          (track.GetEnd, track.SetEnd)):
            point = get()
            if _supported(point, track, board, vias, tracks, epsilon):
                continue
            for footprint in board.GetFootprints():
                for pad in footprint.Pads():
                    if pad.GetNetCode() != track.GetNetCode():
                        continue
                    if not pad.IsOnLayer(track.GetLayer()):
                        continue
                    box = pad.GetBoundingBox()
                    reach = track.GetWidth() // 2
                    if not (box.GetLeft() - reach <= point.x
                            <= box.GetRight() + reach
                            and box.GetTop() - reach <= point.y
                            <= box.GetBottom() + reach):
                        continue
                    anchor = pad.GetPosition()
                    set_(pcbnew.VECTOR2I(anchor.x, anchor.y))
                    pad_snapped += 1
                    break
                else:
                    continue
                break

    # Snapping can leave a track whose two ends became the same point. It
    # connects nothing, and DRC reports it crossing whatever it lies on, so
    # it goes before anything else is judged - and before the pruning pass,
    # which can decide to keep a track and then never look at it again.
    # Removed copper is kept alive for the rest of the pass. `Remove` hands
    # ownership to Python, and letting the last reference go frees an item
    # the board's own containers are still holding, which corrupts them.
    discarded = []
    for track in list(board.GetTracks()):
        if track.Type() != pcbnew.PCB_VIA_T and track.GetLength() == 0:
            discarded.append(track)
            board.Remove(track)
    collapsed = len(discarded)

    # The router cuts a corner with a chamfer a few tens of microns long.
    # Copper that short is below anything the fab resolves and reads as a
    # fragment rather than as a route, so each one is folded into the
    # neighbour it meets - and only where a single neighbour meets it away
    # from any pad or via, so a junction is never collapsed, and only while
    # connectivity is unchanged.
    absorbed = 0
    keep_short = set()
    while True:
        board.BuildConnectivity()
        baseline = board.GetConnectivity().GetUnconnectedCount(True)
        vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        tracks = [t for t in board.GetTracks()
                  if t.Type() != pcbnew.PCB_VIA_T]
        move = None
        for track in tracks:
            if track.m_Uuid.AsString() in keep_short:
                continue
            if track.GetLength() >= pcbnew.FromMM(MIN_SEGMENT_MM):
                continue
            if _entry_geometry(track, board, vias):
                continue
            move = _absorption(track, board, vias, tracks, epsilon)
            if move is not None:
                break
            keep_short.add(track.m_Uuid.AsString())
        if move is None:
            break
        fragment, neighbour, setter, previous, target = move
        setter(target)
        discarded.append(fragment)
        board.Remove(fragment)
        board.BuildConnectivity()
        if board.GetConnectivity().GetUnconnectedCount(True) > baseline:
            setter(previous)
            discarded.pop()
            board.Add(fragment)
            board.BuildConnectivity()
            keep_short.add(fragment.m_Uuid.AsString())
            continue
        absorbed += 1

    # The search falls back to a 5 mil track where it cannot fit the width it
    # was given. That is below the floor this board declares, so it is
    # brought up to the floor - not to the net class's width, which is a
    # preference rather than a limit, and widening to it would move copper
    # the clearance check has already accepted.
    floor = pcbnew.FromMM(build.DESIGN_RULES["min_track_width"])
    widened = 0
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        if track.GetWidth() >= floor:
            continue
        track.SetWidth(floor)
        widened += 1

    # Every via the search added is the board's own via. The router narrows
    # one where it cannot fit the declared size, which produces a hole the
    # board's declared fabrication process does not offer; the declared size
    # is restored, and if that no longer fits, the clearance check that runs
    # next is what says so.
    resized = 0
    for item in board.GetTracks():
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        if item.GetWidth(pcbnew.F_Cu) >= pcbnew.FromMM(layout.VIA_DIAMETER_MM) \
                and item.GetDrill() >= pcbnew.FromMM(layout.VIA_DRILL_MM):
            continue
        item.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(layout.VIA_DIAMETER_MM))
        item.SetDrill(pcbnew.FromMM(layout.VIA_DRILL_MM))
        resized += 1

    # A branch the search started in the middle of another track is a
    # junction to the connectivity - the copper overlaps - and a bare end to
    # the checker, which asks what meets the end point rather than what the
    # copper covers. The track it lands on is split there, so the two agree.
    # No copper moves: one segment becomes two collinear segments of the
    # same width meeting at the point the branch already touched.
    split = 0
    for _ in range(400):
        tracks = [t for t in board.GetTracks()
                  if t.Type() != pcbnew.PCB_VIA_T]
        target = None
        for track in tracks:
            for point in _endpoints(track):
                for other in tracks:
                    if other.m_Uuid.AsString() == track.m_Uuid.AsString():
                        continue
                    if other.GetNetCode() != track.GetNetCode():
                        continue
                    if other.GetLayer() != track.GetLayer():
                        continue
                    if any(math.hypot(point.x - end.x, point.y - end.y)
                           <= epsilon for end in _endpoints(other)):
                        continue
                    distance, fraction = _point_to_segment(
                        point, other.GetStart(), other.GetEnd())
                    if distance > epsilon or not 0.0 < fraction < 1.0:
                        continue
                    target = (other, point)
                    break
                if target is not None:
                    break
            if target is not None:
                break
        if target is None:
            break
        other, point = target
        tail = pcbnew.PCB_TRACK(board)
        tail.SetStart(pcbnew.VECTOR2I(point.x, point.y))
        tail.SetEnd(other.GetEnd())
        tail.SetLayer(other.GetLayer())
        tail.SetNet(other.GetNet())
        tail.SetWidth(other.GetWidth())
        tail.SetLocked(other.IsLocked())
        other.SetEnd(pcbnew.VECTOR2I(point.x, point.y))
        board.Add(tail)
        split += 1

    # Splitting can leave a piece the router had already drawn separately -
    # the same copper twice, which reads as two conductors where there is
    # one. The second copy is dropped; the copper the board carries is
    # unchanged because the copy covered nothing the original did not.
    duplicates = 0
    seen = {}
    for track in list(board.GetTracks()):
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        ends = tuple(sorted(((track.GetStart().x, track.GetStart().y),
                             (track.GetEnd().x, track.GetEnd().y))))
        key = (track.GetNetCode(), track.GetLayer(), track.GetWidth(), ends)
        if key in seen:
            discarded.append(track)
            board.Remove(track)
            duplicates += 1
            continue
        seen[key] = track

    # Prune what the router left unattached. A track whose removal would
    # break the net is kept and skipped rather than ending the pass, because
    # one such track used to hide every dangling end behind it.
    removed = 0
    keep = set()
    while True:
        board.BuildConnectivity()
        baseline = board.GetConnectivity().GetUnconnectedCount(True)
        vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        tracks = [t for t in board.GetTracks()
                  if t.Type() != pcbnew.PCB_VIA_T]
        victim = None
        for track in tracks:
            if track.m_Uuid.AsString() in keep:
                continue
            if all(_supported(point, track, board, vias, tracks, epsilon)
                   for point in _endpoints(track)):
                continue
            victim = track
            break
        if victim is None:
            break
        uuid = victim.m_Uuid.AsString()
        discarded.append(victim)
        board.Remove(victim)
        board.BuildConnectivity()
        if board.GetConnectivity().GetUnconnectedCount(True) > baseline:
            discarded.pop()
            board.Add(victim)
            board.BuildConnectivity()
            keep.add(uuid)
            continue
        removed += 1

    # The router adds copper the pours were not knocked out around, so the
    # fill is recomputed here rather than left describing earlier copper.
    layout.fill_zones(board)
    pcbnew.SaveBoard(path, board)
    return {"endpoints_snapped": snapped,
            "junctions_split": split,
            "duplicate_tracks_removed": duplicates,
            "fragments_absorbed": absorbed,
            "endpoints_snapped_to_pads": pad_snapped,
            "collapsed_tracks_removed": collapsed,
            "narrow_tracks_widened": widened,
            "undersized_vias_restored": resized,
            "dangling_tracks_removed": removed,
            "zones_refilled": len(list(board.Zones()))}


if __name__ == "__main__":
    for path in run():
        sys.stdout.write(path + "\n")
