# Architecture — CAN-FD Sensor/Control Node

**A worksheet, not a design.** Every line below is a question this board has to
answer, and none of them is answered here. Nothing in this file is a
recommendation, and the order of the sections carries no preference.

The questions were derived from [the brief](../BRIEF.md) and from what this
board is meant to stress in the benchmark:

- CAN differential pair
- 24V input protection
- termination
- MCU clocking

Those are the places where a wrong answer shows up in copper.

Answer them in this file as the design is made, each answer carrying the
evidence that supports it, and record the corresponding choice against its
`OPEN-nn` entry in [board/requirements.md](../board/requirements.md). An answer
without evidence is a guess wearing a document's clothes — and this benchmark is
allowed to refuse an unsupported claim rather than invent one.

## CAN-FD controller and transceiver split

- Which MCU is chosen, and what evidence shows its CAN-FD peripheral meets the intended bit rates?
- Which external transceiver is chosen, and does its loop delay and timing symmetry support the chosen data-phase rate?
- At what supply voltage does the transceiver run, and does the MCU's CAN TXD/RXD interface match that level without translation?
- Which transceiver mode pins (standby, silent, enable) are driven, and what is the power-on default state of the bus driver?
- Is the transceiver inhibited from driving the bus during MCU reset or before firmware is loaded, and what makes that necessary - or unnecessary - for this node?

## MCU clocking and CAN-FD bit timing

- What clock source feeds the CAN-FD peripheral, and what is its total frequency tolerance over temperature, ageing and supply?
- What arbitration and data-phase bit rates are targeted, and what sample points and synchronisation-jump-width follow from them?
- Does the chosen oscillator tolerance satisfy the bit-timing tolerance budget for those rates, and what calculation shows it?
- If a crystal or resonator is used, what load-capacitance and drive-level values does the datasheet require, and how is the oscillator loop laid out?
- Is the clock accurate enough for CAN-FD at the fastest rate the design claims to support, or does the claim need narrowing?

## CANH/CANL differential pair routing

- What differential impedance target, if any, is adopted for CANH/CANL, and what stackup and geometry produce it?
- How are the pair's length matching, spacing and via count controlled between connector, protection, termination and transceiver?
- Does the chosen stackup provide a continuous reference plane under the pair for its whole run, and if it does not, what return path do the pair's signals actually take?
- How is the pair kept away from the power-conversion stage, the low-side output return currents and the digital I/O?
- What order do connector, ESD device, common-mode filtering (if any) and termination appear in along the pair?

## Switchable 120-ohm termination

- What mechanism makes the 120-ohm termination switchable, and can its state be determined by inspection or by firmware?
- Is termination implemented as a single resistor or split with a common-mode node, and what justifies that choice?
- What resistor tolerance and power rating are required, and under what bus fault condition is the worst-case dissipation calculated?
- Does the termination stub add measurable discontinuity at the chosen data-phase rate, and how is the stub minimised?
- What is the default shipped state of the termination selector, and how - if at all - is that state made discoverable to a user (silkscreen, documentation, firmware readback)?

## Bus connector protection zone

- Which ESD protection device class is used on CANH/CANL, and what discharge levels does its datasheet support?
- What line capacitance does the protection add, and is that acceptable at the chosen CAN-FD data-phase rate?
- How is 'near the connector' satisfied concretely - what is the physical distance from connector pins to protection and to termination, and where is that verified?
- Does the ESD return path go to the intended reference with a short, low-inductance connection?
- Is the CANH/CANL adjacency requirement met at the connector pin assignment, and is the rest of the connector pinout documented?

## 24 V input protection and power entry

- What reverse-polarity method is used, and what is its forward drop or on-resistance at the full input current?
- What transient environment is assumed for the 24 V input, and what evidence supports that assumption?
- What clamp device is chosen, what is its standoff and clamping voltage relative to the downstream regulator's absolute maximum, and what energy must it absorb?
- Is there a fuse or current limit, and what fault does it protect against?
- What input filtering is present, and is the input capacitance stable if the supply is hot-plugged?

## Local power conversion and rails

- What rails does the board need, at what currents, and how is that budget derived from the chosen MCU, transceiver, inputs and outputs?
- What regulator topology converts the input supply to the main rail, what is that regulator's input source, and what efficiency does its datasheet show at the actual load points?
- If the chosen topology switches, what switching frequency is used, and how does that frequency interact with the CAN-FD signalling and the digital inputs?
- What high-di/dt loops, if any, does the chosen regulator create, and how are they kept small and away from the bus pair and other sensitive nodes?
- What is the power-up sequence and rail settling behaviour, and what does it imply for when the transceiver can safely drive the bus?

## Four digital inputs

- What input signal type and voltage levels are the four inputs designed to accept, and what fixes that choice?
- What sets the switching threshold and hysteresis, and how are the inputs protected against overvoltage and ESD at the field connector?
- Is any isolation provided between field inputs and logic, and if not, what is the rationale?
- Is any input filtering provided, what disturbance is it sized against (contact bounce, industrial noise, or something else), and what does it cost in response time?
- What is the input current per channel at the design input voltage, and does it fit the power budget?

## Four low-side outputs

- What switch device drives each low-side output, and what voltage and current rating does it need for the intended demonstration loads?
- What load types are the demonstration outputs specified to drive, and if any of them are inductive, how is the turn-off energy handled - freewheel diode, active clamp, or reliance on device avalanche?
- What is the worst-case per-channel and total dissipation, and what copper area or thermal path handles it?
- How are output return currents routed so they do not disturb the CAN pair or the input thresholds?
- Are the outputs protected against short circuits, and is any fault fed back to the MCU?

## Stackup, layer count and grounding

- Is the board 2-layer or 4-layer, and what specifically drives that decision for this node?
- What stackup does the chosen fabricator offer, and what does it give for the differential pair's impedance?
- How are the 24 V/protection domain, the power-conversion stage, the logic and the bus interface partitioned on the board?
- Where do grounds join, and what path do ESD and surge currents take from the connector to the reference?
- Do the chosen trace widths and clearances meet the fabricator's capability and the creepage needed at 24 V and at bus fault voltages?

## Connectors, outline and mechanical placement

- What connector is used for the CAN bus, and how does its pinout place CANH and CANL adjacent?
- Are power, bus and field I/O on separate connectors, and how is mis-mating prevented?
- What board outline, mounting holes and component-height envelope are chosen, and what constrains them?
- Where does each connector sit on the outline so that field wiring does not run over the sensitive bus front end?
- Is any silkscreen marking provided for the termination selector, the input polarity and the I/O channel numbering, and what decides which of those need marking at all?

## Bring-up, test and toolkit integration

- What test points and access are needed to observe CANH/CANL, the rails and the output states during bring-up?
- How is bus communication verified end to end, and against what other node or tool?
- What checks confirm the termination selector, reverse-polarity protection and each of the eight I/O channels?
- How is the board's configuration expressed for the shared PCBA_AutoDesignAndTest toolkit without pushing board-specific logic into the toolkit?
- What outputs does the chosen design and test flow actually generate, and which of them are disposable working files versus artefacts kept in the repository?

## Answers still owed

All of them. See [status.md](status.md).
