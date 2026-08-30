# Benchmark entry — board 6 of 32

[metadata.json](metadata.json) is the supplied catalogue entry for this board,
preserved byte for byte from the seed pack. It is the same record that appears
in `boards_index.json` in
[PCBA_AutoDesignAndTest_Bench](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench), and the two must agree.

| | |
|---|---|
| Repository | `PCBA_CAN_FD_Node` |
| Board id | `can_fd_node` |
| Category | industrial-network |
| Difficulty | 2 / 5 |
| Brief detail | 3 / 5 |
| Likely layer count | 2 or 4 |
| Primary stressors | CAN differential pair, 24V input protection, termination, MCU clocking |

`difficulty` is how hard the board is. `detail` is how much of it the brief
states — and a low `detail` is not a low bar. A detail-1 brief leaves the
architecture open on purpose, and an agent that fills the silence with invented
user requirements has failed the board more thoroughly than one that designs it
badly.

At difficulty 2/5 and brief detail 3/5 in the `industrial-network` category, this board tests whether an agent can execute a well-understood industrial node without over-claiming: the named stressors are the CAN differential pair, 24 V input protection, termination, and MCU clocking. The brief is specific about block-level content and one connector-region placement rule, but deliberately silent on parts, rails, bit rates, ratings, geometry and stackup — so the benchmark measures how cleanly an agent separates the stated architecture from the many unstated choices, and whether it can substantiate a differential pair, a protection front end, and a clock accurate enough for CAN-FD bit timing with real evidence rather than assertion.

## What goes here

Compact results only: metrics, verdicts, and the commit each was measured at.
The evidence for a result is the artefact the toolkit recomputes, not a summary
of it.

Routing search output, candidate pools, build trees and field-solver dumps do
**not** go here. They are ignored by [.gitignore](../.gitignore) and are
regenerated from what is committed. Thirty-two repositories share one benchmark
clone; weight here is paid thirty-two times.

## Protocol

The attempt protocol is defined once, in the umbrella repository, so that
thirty-two boards cannot drift into thirty-two protocols. See
[PCBA_AutoDesignAndTest_Bench/BENCHMARK.md](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench/blob/main/BENCHMARK.md).
