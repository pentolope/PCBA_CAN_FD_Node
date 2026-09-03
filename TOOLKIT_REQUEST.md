# Toolkit requests from 06_PCBA_CAN_FD_Node

What this board needed from `PCBA_AutoDesignAndTest` and did not find, written as
board-agnostic capabilities. Every item names the concrete thing that happened
here, because a request without one is a preference.

Nothing below asks for anything about CAN, about this board's parts, or about a
24 V industrial node. Where a request came from a specific conductor, the
generalisation is stated.

Ordered by how much each one would change what a board can do, not by size.

---

## A. Copper the design authors itself

The generated-board workflow says the design source authors the geometry whose
shape is a requirement and the router draws the rest. The toolkit supports the
second half well and the first half by accident.

### A1. Authored copper as a declared, verified input

**What happened.** The design drew the bus pair, the switch node, the
termination centre, each field output, the input-rail capacitor link and the
field supply, then handed the board to the router with those nets left out of
`--nets`. The router rewrote the field supply anyway: a straight 1.0 mm corridor
came back as a diagonal through the back layer with a dangling via. The
router's `--keep-input-copper` flag reads as the fix and is not one — its help
text scopes it to "the post-route cleanup passes … never remove or rewrite it",
not to the rip-up engine. The behaviour that does work is undocumented in the
toolkit's own interface: `py_router/protected_nets.py` treats a net carrying any
KiCad-locked segment as protected, and `'locked'` has no override. Finding that
cost three full routing runs.

**Request.** A first-class notion of authored copper in the toolkit's routing
wrapper:

- one documented way to say "this copper is the design's; the search may not
  move it", rather than a lock flag whose protective meaning is an
  implementation detail of a vendored router;
- a post-route check that authored copper is returned unchanged — geometry,
  layer and width — and a refusal, not a warning, when it is not;
- the same notion available per piece, not only per net. A board that authors
  one conductor of a net and lets the search finish the rest currently has to
  choose between locking the whole net and protecting nothing.

**Why general.** Any board whose topology is a requirement rather than a result
has this problem, and the failure is silent: the copper comes back connected, so
every connectivity check passes while the requirement is gone.

### A2. A safe removal helper for post-router transforms

**What happened.** The board's tidy pass removes degenerate and dangling
tracks. `board.Remove(item)` hands ownership to Python, and when the last
reference to a removed item was dropped, the board's own containers were left
corrupt: the next `board.GetTracks()` raised
`TypeError: 'SwigPyObject' object is not iterable`, from inside pcbnew's
`list(self.Tracks())`. The symptom appears at an unrelated line several
statements later, which makes it expensive to diagnose. The fix is to keep every
removed item alive for the rest of the pass.

**Request.** A `pcbqa` helper that owns board mutation for these passes —
remove, re-add on failure, and keep custody of removed items — so that no board
has to rediscover this. Every board that copies a tidy pass inherits the bug
today.

### A3. One definition of "attached", and the transforms that satisfy it

**What happened.** Three parts of this pipeline disagree about when a track end
is connected:

| Asker | Rule |
|---|---|
| KiCad connectivity | copper overlaps — a T into the middle of a track counts |
| KiCad DRC | `track_dangling` for that same T |
| `pcbqa/gates/g_geometry.py` | the end point must hit a pad, a via, or another segment's body |

So a board can be simultaneously fully connected, warned about by DRC, and
failed by `ROUTE.GEOMETRY_HYGIENE`. Reaching a clean board needed three
transforms written here: split a track where another track's end stands on it,
drop the exact duplicate that splitting can create, and pull a track end onto a
pad anchor when the end lies outside the pad's bounding box but the track's own
copper overlaps the pad (the case here was 0.03 mm — connected for KiCad,
dangling for the gate).

**Request.** Move these into the toolkit as a supported post-router
normalisation, with the gate and the transform sharing one definition. None of
the three is board-specific; all three are consequences of how grid routers emit
copper.

### A4. Reconcile the router's own success report with the checker

**What happened.** One attempt reported `routed: 41`, `pad_pairs_open: {count:
0}`, `failed: 0` — and the adopted board's DRC found `XIN` unconnected to `U1`
pad 2. The router believed it had finished a net it had not. Because the
board-side pipeline judges the candidate afterwards, this was caught, but only
as a bare unconnected item with no hint that the router had claimed otherwise.

**Request.** Have the routing wrapper compare the router's summary against the
adopted board's connectivity and report the disagreement as its own finding.
A search that mis-reports completion is a different failure from a search that
runs out of room, and they deserve different responses.

### A5. Replay the transform stages without re-routing

**What happened.** Nine attempts at roughly a minute each, and the pipeline was
re-run four times for changes that touched only the tidy pass. The recorded
candidates are all on disk under `candidates/route-current/attempt-NN/`, with
digests, so nothing had to be re-searched.

**Request.** A supported way to re-run the post-router stages over recorded
candidates and re-judge them, with the provenance record noting that the search
was replayed rather than repeated. Iteration on a transform is currently paid
for at the price of the search.

---

## B. Pours, planes and the reference

### B1. Report pour islands, not just their symptom

**What happened.** After one routing attempt the input-rail pour split in two
and stranded a capacitor's pad on a 12.5 mm² island. What the pipeline said was:

```
unconnected_items | Zone [V24] on F.Cu, priority 1 ; Zone [V24] on F.Cu, priority 1
```

Two identical items naming the same zone. Diagnosing it needed a script that
refilled the zones, walked `GetFilledPolysList`, and tested every pad of the net
for membership.

**Request.** A gate, or a measurement inside an existing one, that reports each
pour's island count with each island's area and the pads it holds. The failure
is common on any board with a pour on a routed layer, and the message a board
gets today does not say what happened.

### B2. Reference continuity without declaring a timing interface

**What happened.** This board's brief requires the bus pair to run "over an
unbroken return path". I believed the toolkit could not measure that and left
the requirement resting on keepout rule areas that cover 8.3 mm of a 25 mm run.
That was wrong: `pcbqa/gates/g_timing.py` already measures unreferenced length
per path and compares it against `timing.interfaces.<name>.max_unreferenced_mm`,
and `_limit_for` treats the delay and skew limits as optional — so the check is
reachable with routes and a continuity limit alone.

What made it unreachable in practice is the name. A board with no timing
requirement has no reason to look inside `timing`, and declaring an interface
called a timing interface to express a return-path requirement misrepresents
what the board is asking for.

**Request.** Expose reference continuity under a neutral declaration — the same
machinery, keyed on nets or paths, without the timing framing — and have the
path-integrity check follow it. Return-path continuity is an electromagnetic
requirement that plenty of boards have while having no timing budget at all.

### B3. A pad-sweep stitcher over the primitive that already exists

**What happened.** `pcbqa/critical_topology.py` has `stitch_to_plane`: a
verified escape plus via, honouring copper clearance, the mask annulus target,
hole-to-hole and keepouts. This board did not use it. It hand-wrote the same
thing — obstacle model, clearance sweep, mask target, keepout spans, retry
positions — because what a board actually needs is one level up: *stitch every
surface pad of this net to this plane, and tell me which ones could not be
stitched and why*. Earlier boards did the same.

**Request.** That driver, over the existing primitive: a net-wide sweep with a
per-pad result. The single-site function is the hard part and it is already
written; three boards have now reimplemented the loop around it.

---

## C. Extraction and models

### C1. Traversals that pass through pads

**What happened.** Two conductors on this board deliberately run *through* a
pad: the field supply passes through its probe's pad, and each field output
passes through its clamp's pad. `extract.path_resistance` refuses both:

```
traversal element 15 on net 'VFIELD' begins and ends in one electrical node;
its series resistance would be fictitious, and the path-scoped model refuses
```

The refusal is right. The consequence is that the board decomposes the
conductor into hops by hand, sums the resistances, sums the uncertainties, and
re-assembles a record the toolkit could have produced.

**Request.** Accept a chain of pads, not only two endpoints, and return the
summed record with each hop's claim retained. Running a conductor through a
probe or a clamp is ordinary practice, not a special case.

### C2. Via barrel resistance as a supported model

**What happened.** Every traversal crossing a via comes back as a lower bound,
because barrels are omitted and the omission is recorded. A lower bound cannot
satisfy a `<=` requirement, so the board wrote its own barrel model — drill
diameter, board thickness, an assumed 18 µm plating, annealed copper — to turn
the measurement back into an upper bound. That model is now this board's, which
means the next board writes it again, differently.

**Request.** A first-class via-barrel resistance model with the plating
thickness as a declared, provenance-bearing physical input alongside copper
thickness and board thickness, so `path_resistance` can return a bounded
quantity instead of an unusable one. See E3 for where the plating number should
come from.

### C3. Tier-1 capacitance and inductance

**What happened.** The extraction states plainly that it claims no capacitance
and no inductance. Two questions the architecture asks could not be answered:
"did a switching loop become too inductive?" (§22) and whether the routed bus
pair's own capacitance eats into a cable budget. The buck's hot loop on this
board was *placed* for compactness and never measured; the bus budget still
counts the cable and the devices and not the board.

The pieces exist — `transmission_line.py`, `propagation.py`, `stackup_physical`
reference geometry — but none of them is reachable as a claim about an arbitrary
conductor's parasitics.

**Request.** Tier-1 analytic C and L, produced as claims with their model named,
for two shapes that recur everywhere: per-length capacitance of a conductor over
its reference, and loop inductance of a closed current path identified by its
pads. Both are geometry plus a documented closed form, which is what tier 1 is
defined as.

### C4. One way to build the model registry a manifest declares

**What happened.** `simulation.extracted_models` is the right design — the model
is measured from the board under validation, so no file can go stale. But a
board that wants to run the same scenario in its own test suite has to
reimplement the gate's registry assembly, which this board did. The test and the
gate now agree by inspection rather than by construction.

**Request.** A supported entry point that returns the registry a manifest
declares, for a given board, so the gate and the board's tests call the same
code.

### C5. `geom.configure` should not be a trap

**What happened.** Calling `extract.path_resistance` outside a gate fails with
`UnsupportedGeometry: no polygon chord error has been configured`. The gates
configure it from the manifest's geometry profile; nothing else does, and the
error names a setting rather than the manifest field it comes from.

**Request.** Have the extraction entry points resolve the tolerance from the
manifest, or say which manifest field is missing.

### C6. More verified monotonic templates for measurement knowledge

**What happened.** A post-layout scenario fed by an extracted model whose
resistance is a lower bound is refused unless the measurement declares its
knowledge. Declaring `derived` is then refused too, because
`derive_measurement_knowledge` supports exactly one circuit: source → one series
element → one load. Anything real ends up declaring `assumed` with a prose
monotonicity argument, which is weaker evidence than the circuit actually
supports.

**Request.** Extend the template set to the shapes that occur constantly — a
series chain of two-terminal elements, a load among several parallel loads, a
divider with a shunt — so a real network can keep theorem-level provenance
instead of dropping to an assumption the first time it has four elements.

---

## D. Checks a board cannot make for itself

### D1. Conductor and via current capacity

**What happened.** The field supply carries 1 A through a 1.0 mm track and
through two vias, and nothing anywhere checks that this is acceptable. The
board's own claims cover resistance and voltage drop; current capacity and
temperature rise are simply absent from the toolkit — no ampacity model, no
IPC-2152-style width-versus-rise table, nothing for a via in a current path.

**Request.** A current-capacity check over declared current-carrying paths,
taking the current from the design's own claims and the geometry from the board,
with the temperature-rise basis stated. This is the single most load-bearing
unchecked thing on this board, and it is unchecked on every board the toolkit
has produced.

### D2. Thermal

**What happened.** The board makes dissipation claims against package ratings
and stops there. No claim states a junction temperature, and three parts that
should have one — the converter, the transceiver, the device carrying the whole
board current — have no dissipation claim at all. An earlier board in this bench
wrote `design/thermal.py` by hand, including the reasoning the architecture
demands: that a junction temperature from a datasheet's θJA is conditional on
boundary conditions this board does not reproduce, so what is reported is the
factor by which the thermal path could be worse before the limit is reached.

**Request.** That pattern, toolkit-owned: dissipation collected from the claim
set, copper spreading from the board, junction temperature reported as a
conditional margin with the θJA validity recorded, and board temperature rise
reported as UNKNOWN until a solve or a measurement exists. The architecture asks
for exactly this and names the trap; a per-board implementation means each board
gets it right or wrong on its own.

### D3. Voltage-dependent conductor spacing

**What happened.** This board carries 30 V continuously and 48.4 V clamped on
copper spaced 0.15 mm, and nothing states that this is adequate. The obvious
source, IPC-2221 Table 6-1, is not redistributable. The bench's one frozen
substitute — the TI seminar papers reproducing IEC 60664-1 — bottoms out at a
500 V impulse row, far above anything on this board, so interpolation from it
would be invention.

**Request.** A freezable spacing basis in the fabricator or evidence layer that
reaches down to low voltages, so that boards below the mains-isolation range can
make a spacing claim instead of leaving one of the most basic physical
requirements unstated. Every board the bench produces has this hole right now.

---

## E. Requirements, statements and release

### E1. A requirements register with an enforced join

**What happened.** This board's 225 claims are judged against 67 distinct
requirement names, and every one of them records its source as the bare string
`BRIEF.md`. Nothing distinguishes what the brief actually demanded from what the
design derived, chose, or assumed — the architecture's four statement types
collapse into one string, and the two open choices the brief explicitly left
(how termination switches; which MCU and transceiver) survive only in code
comments and a commit message.

An earlier board built this: a register of every requirement with its kind, its
origin as a brief anchor, its rationale, its alternatives, the verification
methods that establish it, and whether a physical test is still required —
joined to the claim set in both directions, so an unregistered requirement and
an unjudged registration are both errors.

**Request.** The schema and the join as a toolkit gate. Board-agnostic by
construction: the register's shape does not depend on what the board does. What
makes it a toolkit concern rather than a per-board one is that the join has to be
enforced, and today it is enforced only where a board happened to write the test.

### E2. Verification method, physical test, and external dependencies

**What happened.** Two things on this board can only be settled physically —
oscillator start-up margin and discharge survival — and both are recorded as
sentences inside assumption text on unrelated claims. There is no structured
place to say "this requirement needs a physical test", so nothing can count
them, list them, or check that the list is complete. The architecture asks
specifically that an agent be able to say physical validation is still required.

Separately, the assembly section asks that steps which cannot be validated
locally — the fabricator's own assembly preview being the example — be recorded
as external or manual release dependencies rather than silently assumed. There
is nowhere to record one.

**Request.** A verification-method classification per requirement (the
architecture's own list), a physical-test register derived from it, and an
external-dependency record that release closure can report on. A release that
lists what still has to be proven on a bench is worth more than one that does
not mention it.

### E3. Fabricator catalogue: hole-wall plating

**What happened.** The approved JLCPCB catalogue states finished copper for
outer and inner layers, mask thickness, and copper-weight equivalence. It says
nothing about the plating in a hole. So the via-resistance bound in C2 rests on
an assumption where every other physical input on this board rests on evidence.

**Request.** Carry hole-wall plating thickness in the catalogue when the
fabricator states it, so via models can be evidence-backed like everything else.

---

## What is deliberately not requested

- Anything about CAN FD, split termination, or this board's parts. Where a
  request came from one of them, the general shape is what is asked for.
- Tier 2 and 3 extraction, and EM. Nothing on this board is
  impedance-controlled, so I would be asking for capability I cannot judge.
- Digital or MCU simulation. This board's firmware-facing behaviour is covered
  by a safe-state scenario, and the firmware lives elsewhere.
- Optimisation feedback loops. The architecture puts those on the toolkit's own
  roadmap, and nothing here is blocked on them.

---

## If only three were done

**A1** (authored copper), **D1** (current capacity) and **E1** (requirements
register). The first stops a class of silent requirement loss that no existing
check catches; the second closes the largest unchecked physical question on this
board and on every board like it; the third is what makes the difference between
a board that passes its own tests and a board whose claims a reader can trace
back to what was actually asked for.
