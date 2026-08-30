# Requirements — CAN-FD Sensor/Control Node

Two lists. The difference between them is the whole point of this file.

A **fixed requirement** is something [BRIEF.md](../BRIEF.md) asks for. Each one
below quotes the brief text that substantiates it; if a statement cannot be
quoted, it is not a requirement here. An **open decision** is a choice the brief
deliberately left to whoever designs this board.

> Missing details are design freedom, not permission to fabricate unstated user
> requirements.

Promoting a decision into a requirement is the failure this file exists to
prevent. Record a choice under the decision it answers, with the reasoning that
made it — never by adding it to the list above.

Bound to `BRIEF.md` SHA-256 `3897ccfaae068a75cbd3eae3186d01ac4c7f7dafd298f4a1a979556b659bc86c`.

## Fixed by the brief

### REQ-01 — The board is a general-purpose CAN-FD node intended for a 24 V industrial system.

Brief text:

> Design a general-purpose CAN-FD node for a 24 V industrial system.

### REQ-02 — The controller is a modern MCU that provides CAN-FD.

Brief text:

> for a 24 V industrial system. Use a modern MCU with CAN-FD

### REQ-03 — The bus physical layer is an external CAN-FD transceiver, i.e. a device separate from the MCU.

Brief text:

> an external CAN-FD transceiver, switchable 120-ohm termination

### REQ-04 — The board provides 120-ohm bus termination that is switchable, not permanently fitted.

Brief text:

> switchable 120-ohm termination, ESD protection at the bus connector

### REQ-05 — ESD protection is provided at the bus connector.

Brief text:

> ESD protection at the bus connector, reverse-polarity and transient protection on the 24 V input

### REQ-06 — The 24 V input has reverse-polarity protection.

Brief text:

> reverse-polarity and transient protection on the 24 V input, and an efficient local regulator.

### REQ-07 — The 24 V input has transient protection.

Brief text:

> ESD protection at the bus connector, reverse-polarity and transient protection on the 24 V input

### REQ-08 — The board includes an efficient local regulator. The brief does not state the regulator's input source, topology or output rails.

Brief text:

> and an efficient local regulator. Provide four digital inputs

### REQ-09 — The board provides four digital inputs.

Brief text:

> Provide four digital inputs and four low-side outputs for demonstration loads.

### REQ-10 — The board provides four low-side outputs, intended to drive demonstration loads.

Brief text:

> four low-side outputs for demonstration loads. The CAN connector must place CANH/CANL adjacent

### REQ-11 — The CAN connector places CANH and CANL on adjacent pins.

Brief text:

> The CAN connector must place CANH/CANL adjacent and keep protection/termination near the connector.

### REQ-12 — Bus protection and termination are placed near the CAN connector.

Brief text:

> adjacent and keep protection/termination near the connector.

### REQ-13 — Where the brief is silent, the design agent makes and documents reasonable engineering decisions instead of inventing hidden user requirements; stated requirements are authoritative.

Brief text:

> Treat stated requirements as authoritative; where the brief leaves choices open, make and document reasonable engineering decisions rather than inventing hidden user requirements.

### REQ-14 — The repository stays a consumer of the shared PCBA_AutoDesignAndTest toolkit; board-specific logic does not accumulate in the toolkit.

Brief text:

> The repository should remain a consumer of the shared `PCBA_AutoDesignAndTest` toolkit rather than accumulating board-specific logic in the toolkit.

## Open — the design agent decides

### OPEN-01 — Which MCU (vendor, family, part number, package, memory, pin count) provides the CAN-FD controller.

The brief asks only for 'a modern MCU with CAN-FD' and names no vendor, family, part or package.

*Decision:* **not yet made.**

### OPEN-02 — Which external CAN-FD transceiver is used, and which of its optional features (silent/standby mode, wake, bus-fault reporting, split/biasing pin) the design relies on.

The brief requires an external CAN-FD transceiver but names no device and no feature set.

*Decision:* **not yet made.**

### OPEN-03 — MCU clock source - internal oscillator, crystal, or oscillator module - its frequency, and the frequency-tolerance budget over temperature and life.

'MCU clocking' is listed as a stressor in the metadata, but the brief states no clock source, frequency or tolerance.

*Decision:* **not yet made.**

### OPEN-04 — Arbitration-phase and data-phase bit rates, sample points and the resulting bit-timing/oscillator-tolerance margin.

The brief names no bit rate, bus length, or node count for the CAN-FD network.

*Decision:* **not yet made.**

### OPEN-05 — How termination is switched (jumper, DIP switch, solder link, electronically controlled) and whether it is a single resistor or split termination with a common-mode capacitor.

The brief fixes the value as 120 ohm and requires it to be switchable, but does not state the switching mechanism or the termination topology.

*Decision:* **not yet made.**

### OPEN-06 — Bus ESD protection device class and its ratings - clamping voltage, contact/air discharge level, and line capacitance budget against CAN-FD data-phase edges.

The brief requires ESD protection at the bus connector but states no immunity level, device type or capacitance limit.

*Decision:* **not yet made.**

### OPEN-07 — The 24 V front-end topology: reverse-polarity method (series diode, P-FET, ideal-diode controller), transient clamp choice, fusing or current limiting, and input filtering.

The brief names the two protections but not the circuit, the transient energy or surge level to survive, or whether fusing is required.

*Decision:* **not yet made.**

### OPEN-08 — Regulator topology - linear, switching, or a pre-built module - and, if the chosen topology switches, its switching frequency; plus what 'efficient' means quantitatively for this board and what the regulator's input source is.

The brief calls for 'an efficient local regulator' with no efficiency target, topology, input source, or load condition stated.

*Decision:* **not yet made.**

### OPEN-09 — Rail voltages and the current budget for MCU, transceiver, inputs and outputs, including whether the transceiver and MCU share a rail or need separate ones.

The brief names no supply rail other than the 24 V input and gives no current budget.

*Decision:* **not yet made.**

### OPEN-10 — Digital input conditioning: expected input signal type and levels, whether inputs must tolerate 24 V field signals, thresholds, filtering, protection and any isolation.

The brief states the quantity (four) but nothing about input levels, source type, isolation or protection.

*Decision:* **not yet made.**

### OPEN-11 — Low-side output switch type and ratings: the load types the outputs are specified to drive (resistive, lamp, inductive), device technology, voltage/current capability, any turn-off clamping the chosen load type requires, and any diagnostics or short-circuit protection.

The brief states the quantity (four) and that the loads are for demonstration, but no load type, current, or voltage.

*Decision:* **not yet made.**

### OPEN-12 — Connector selection for the CAN bus, the 24 V power input, and the digital I/O - type, pin count, pitch, current rating, keying, and whether power and bus share a connector.

The brief fixes only that CANH and CANL are adjacent on the CAN connector; no connector family, pin count or pinout is stated.

*Decision:* **not yet made.**

### OPEN-13 — Layer count (2 vs 4), stackup, whether the CANH/CANL pair has a continuous reference plane, and whether it is routed to a controlled differential impedance target.

The metadata says only '2 or 4' layers; the brief states no stackup, dielectric or impedance requirement.

*Decision:* **not yet made.**

### OPEN-14 — Board outline, dimensions, mounting-hole pattern, keepouts, and any enclosure or rail-mount intent.

The brief is silent on mechanical form entirely, apart from the CAN connector's pin adjacency and the protection/termination placement zone.

*Decision:* **not yet made.**

### OPEN-15 — Programming/debug interface, firmware update path, and any status indicators or bus-activity/fault LEDs.

The brief does not mention debug access, bootloading, or indicators.

*Decision:* **not yet made.**

### OPEN-16 — Whether a bus shield/drain connection, common-mode choke, or dedicated bus filtering is provided, and how the bus reference relates to board ground.

The brief requires ESD protection at the connector but says nothing about shielding, common-mode filtering, or grounding scheme.

*Decision:* **not yet made.**

### OPEN-17 — Operating temperature range, EMC/immunity targets, and whether any compliance regime applies.

The brief gives an industrial context but states no environmental range or compliance requirement.

*Decision:* **not yet made.**

### OPEN-18 — Fabrication and assembly constraints: fab vendor and its process capability, assembly side(s), component-height limits, test points and functional-test hooks.

The brief states no manufacturing vendor, process, or test strategy.

*Decision:* **not yet made.**

### OPEN-19 — Whether the transceiver is inhibited from driving the bus during MCU reset, before firmware is loaded, or until rails have settled - and, if so, by what means and on what justification.

The brief names the transceiver but imposes no bus-safety, fail-silent or power-sequencing requirement, so whether such inhibition is needed is the design agent's call.

*Decision:* **not yet made.**

### OPEN-20 — What board markings and documentation, if any, identify the termination selector state, the 24 V input polarity and the I/O channel numbering.

The brief imposes no silkscreen, labelling or user-documentation requirement on the board.

*Decision:* **not yet made.**

## Where a decision gets recorded

1. Answer it under its `OPEN-nn` heading above, with the reasoning and the
   evidence that made the choice.
2. Set `chosen` and `rationale` on the matching entry in
   [requirements.json](requirements.json).
3. Cite the datasheet or standard in [docs/sources.md](../docs/sources.md).

A choice recorded this way stays visibly a choice. That is what lets a later
reader tell this board's engineering apart from its brief.

## Where this board is most likely to be faked

Places where a design run would be tempted to assert something it cannot
substantiate:

- Impedance fabrication: the brief fixes neither layer count nor impedance, so any stated differential target for CANH/CANL must come from a fabricator stackup plus a calculation, not from a remembered number.
- Bit-rate fabrication: the brief names no CAN-FD bit rate. A design that quietly assumes a rate and then declares the clock 'good enough' has invented both the requirement and the margin; the tolerance budget must be shown against whatever rate is chosen.
- Stressor-to-solution conversion: 'ESD protection' and 'transient protection' are outcomes to be met with justified device ratings. Naming a protection part and moving on, with no discharge level, clamp voltage or capacitance budget, is the most likely fake here.
- 'Efficient local regulator' is undefined in the brief. Asserting an efficiency figure or topology without a rail/current budget and a datasheet efficiency curve at the actual load points is unsupported.
- The I/O channels have no stated ratings: input signal levels, 24 V tolerance, load current and load type are all open. Silently assuming field-level inputs, or silently assuming a load type for the low-side outputs, imports requirements the brief never made; whichever signal and load assumptions are adopted must be stated as decisions, and the resulting output protection - clamped or not - justified against them.
- The placement rules are checkable geometry, not prose. CANH/CANL adjacency and 'protection/termination near the connector' must be demonstrated in the layout with actual distances, not claimed in a document.
- Termination must be switchable. A fixed 120-ohm resistor, or a do-not-populate pad relabelled as 'switchable', does not satisfy the brief.
- Outline, mounting, connector families and enclosure are entirely unfixed; presenting any of those choices as if the brief demanded them corrupts the benchmark for later comparison.
