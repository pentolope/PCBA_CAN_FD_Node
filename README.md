# CAN-FD Sensor/Control Node

General-purpose CAN-FD node for a 24 V industrial system: MCU with CAN-FD, external transceiver, switchable termination, four inputs, four low-side outputs.

This repository holds the design problem for `PCBA_CAN_FD_Node`, titled in metadata "CAN-FD Sensor/Control Node": a general-purpose CAN-FD node for a 24 V industrial system. The brief fixes the functional skeleton: a modern MCU with CAN-FD driving an external CAN-FD transceiver, switchable 120-ohm bus termination, ESD protection at the bus connector, reverse-polarity and transient protection on the 24 V input, an efficient local regulator, and four digital inputs plus four low-side outputs for demonstration loads. It also fixes one placement rule — the CAN connector must place CANH/CANL adjacent, with protection and termination kept near that connector. Everything else is open: no part, vendor, connector, package, regulator topology, rail voltage, bit rate, current rating, board outline, or stackup is named, and the layer count is only characterised in metadata as "2 or 4". The design agent must choose and justify those, documenting engineering decisions rather than treating them as pre-existing user requirements.

> **This board has not been designed.** There is no schematic, no layout and no
> part selection here — only the brief, a reading of the brief, and the
> scaffolding a design run needs. That is the intended state of this repository,
> not a gap in it.

## What the brief fixes, and what it leaves open

The brief pins down 14 requirements and deliberately leaves
20 decisions to whoever designs the board. The `Source` column says
which is which: `brief` is quoted from [BRIEF.md](BRIEF.md), `metadata` comes
from the benchmark catalogue, and `open` means the brief does not fix it.

| Aspect | Value | Source |
|---|---|---|
| Board identity | repo PCBA_CAN_FD_Node; title "CAN-FD Sensor/Control Node"; benchmark_id 6 | metadata |
| Board function | General-purpose CAN-FD node for a 24 V industrial system | brief |
| Category / difficulty / brief detail | industrial-network; difficulty 2/5; detail 3/5 | metadata |
| Likely layer count | 2 or 4 | metadata |
| Primary stressors | CAN differential pair, 24V input protection, termination, MCU clocking | metadata |
| Controller | A modern MCU with CAN-FD (no family, part or package named) | brief |
| Bus PHY | External CAN-FD transceiver, separate from the MCU | brief |
| Bus termination | Switchable 120-ohm termination | brief |
| Bus protection | ESD protection at the bus connector | brief |
| 24 V input protection | Reverse-polarity and transient protection on the 24 V input | brief |
| Local power conversion | An efficient local regulator (topology, input source, rails and ratings unstated) | brief |
| Digital inputs | Four | brief |
| Outputs | Four low-side outputs, for demonstration loads | brief |
| CAN connector arrangement and protection zone | CANH/CANL adjacent at the connector; protection and termination kept near the connector | brief |
| Board outline, connector types, rails, bit rates and specific part numbers | Not fixed by the brief - design agent's choice | open |

The full split, with the verbatim brief text substantiating every fixed
requirement, is in [board/requirements.md](board/requirements.md) and
machine-readably in [board/requirements.json](board/requirements.json).

**Missing details are design freedom, not permission to fabricate unstated user
requirements.** A choice the brief left open is recorded as a decision, with its
reasoning — never promoted into a requirement.

## Benchmark position

| | |
|---|---|
| Benchmark id | 6 of 32 |
| Category | industrial-network |
| Difficulty | 2 / 5 |
| Brief detail | 3 / 5 |
| Likely layer count | 2 or 4 |
| Primary stressors | CAN differential pair, 24V input protection, termination, MCU clocking |

At difficulty 2/5 and brief detail 3/5 in the `industrial-network` category, this board tests whether an agent can execute a well-understood industrial node without over-claiming: the named stressors are the CAN differential pair, 24 V input protection, termination, and MCU clocking. The brief is specific about block-level content and one connector-region placement rule, but deliberately silent on parts, rails, bit rates, ratings, geometry and stackup — so the benchmark measures how cleanly an agent separates the stated architecture from the many unstated choices, and whether it can substantiate a differential pair, a protection front end, and a clock accurate enough for CAN-FD bit timing with real evidence rather than assertion.

This repository is one of thirty-two. The suite, the protocol and the results
live in [PCBA_AutoDesignAndTest_Bench](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench).

## Repository layout

| Path | Contents |
|---|---|
| `BRIEF.md` | the supplied brief — authoritative, preserved byte for byte, never edited |
| `board/requirements.md` | what the brief fixes, what it leaves open, and where decisions get recorded |
| `board/requirements.json` | the same split, machine-readable, each fixed requirement bound to brief text |
| `board/manifest.template.json` | the toolkit's minimum manifest, pre-filled for this board |
| `board/toolchain.json` | where this board's build finds KiCad and the router |
| `benchmark/metadata.json` | the supplied catalogue entry — category, difficulty, detail, stressors |
| `docs/architecture.md` | the decisions this board must make, as questions, unanswered |
| `docs/sources.md` | the classes of evidence the design will have to cite |
| `docs/status.md` | what exists, what does not, and what is deliberately absent |
| `candidates/` | disposable search output, ignored by Git |
| `.claude/skills/` | the accountability-review skill [CLAUDE.md](CLAUDE.md) requires before a push |
| `tooling/PCBA_AutoDesignAndTest` | the shared verification/routing/release toolkit, as a pinned submodule |

## Getting the repository

The toolkit is a submodule and carries KiCad Routing Tools as a submodule of its
own, so clone recursively:

```bash
git clone --recursive https://github.com/pentolope/PCBA_CAN_FD_Node.git
```

```bash
git submodule update --init --recursive
```

## Designing the board

Generic verification, routing and release logic is **not** written here. It is
consumed from `tooling/PCBA_AutoDesignAndTest`, which is board-agnostic by
construction and must stay that way; this repository owns the board and nothing
else. Start from
[the toolkit's onboarding guide](tooling/PCBA_AutoDesignAndTest/examples/onboarding.md),
and see [CLAUDE.md](CLAUDE.md) for the rules a design run works under.

```bash
python3 tooling/PCBA_AutoDesignAndTest/run.py preflight
```

## Brief integrity

`BRIEF.md` SHA-256 `3897ccfaae068a75cbd3eae3186d01ac4c7f7dafd298f4a1a979556b659bc86c`

Every quotation in `board/requirements.json` is bound to those exact bytes. If
the brief ever changes, the bindings are stale by construction — which is the
point of recording the digest.
