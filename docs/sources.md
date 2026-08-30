# Sources — CAN-FD Sensor/Control Node

The evidence this board's design will have to cite. **Classes of document, not
documents:** the specific parts are not chosen yet, so naming a datasheet here
would be choosing one.

A number that reaches the board carries its provenance: source, document id or
URL, retrieval date, units, and the condition it applies under. A number without
that is not evidence, and no live network lookup may change a validation or
release result.

| Kind of source | What the design needs from it |
|---|---|
| CAN / CAN-FD physical-layer standard documents | Fix the bus differential and common-mode levels, the 120-ohm termination expectation, bus-length/rate relationships and the bit-timing framework the design must satisfy. |
| CAN-FD transceiver datasheet | Supply range, TXD/RXD levels, loop delay and timing symmetry limits, common-mode range, bus fault and thermal-shutdown behaviour, and mode-pin defaults. |
| MCU datasheet and reference manual | CAN-FD peripheral capability and bit-timing registers, clock-source requirements, GPIO drive and tolerance, package thermals, and pin multiplexing for the eight I/O channels. |
| Clock-source specification (crystal/resonator datasheet or MCU internal-oscillator characteristics) | Frequency tolerance over temperature and ageing, load capacitance and drive level - the inputs to the CAN-FD oscillator-tolerance budget. |
| ESD / TVS protection device datasheets | Clamping and standoff voltages, discharge-level ratings, and line capacitance that must be traded against CAN-FD data-phase edge rates. |
| Transient and surge immunity test standards for industrial equipment | Define the transient levels the 24 V input protection is being designed to survive, rather than an assumed number. |
| Regulator datasheet and its layout/application note, for the converter topology chosen | Efficiency curves at the design's actual input voltage and load points, passive component selection, any layout requirements the topology imposes, and the absolute maximum input rating that the transient clamp must stay below. |
| Low-side switch / MOSFET datasheet | On-resistance, gate drive requirements, avalanche or clamp energy, safe operating area and thermal resistance for the four demonstration outputs. |
| PCB fabricator capability and stackup documentation | Minimum trace/space, dielectric thickness and Dk for 2- or 4-layer options, and whether controlled impedance is offered for the CAN pair. |
| Differential impedance calculation or field-solver output | Ties the chosen CANH/CANL geometry on the chosen stackup to an actual impedance number instead of an asserted one. |
| Connector datasheets | Pinout and pin adjacency for CANH/CANL, current and voltage ratings for the 24 V entry, and field-wiring termination for the digital I/O. |
| Shared PCBA_AutoDesignAndTest toolkit documentation | Whatever the shared toolkit itself states about how a board repository consumes it - its interfaces, configuration inputs and generated outputs - so that this repo remains a consumer rather than accumulating board-specific logic in the toolkit. |

## Recording a source, once one is chosen

Replace the class with the actual document — manufacturer, part number, revision
and date — and state the fact taken from it, in the units the document uses.
Keep the class row: it says why the document was needed.

JLCPCB-wide process limits are **not** recorded here. They live in the toolkit's
`profiles/jlcpcb/`, with their own provenance; this board records only its own
tighter targets and its own selected options. A limit copied into two places is
a rival threshold, and the toolkit has a gate that says so.
