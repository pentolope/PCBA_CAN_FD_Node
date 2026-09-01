# PCBA_CAN_FD_Node — CAN-FD Sensor/Control Node
## Design brief

Design a general-purpose CAN-FD node for a 24 V industrial system. Use a modern MCU with CAN-FD, an external CAN-FD transceiver, switchable 120-ohm termination, ESD protection at the bus connector, reverse-polarity and transient protection on the 24 V input, and an efficient local regulator. Provide four digital inputs and four low-side outputs for demonstration loads. The CAN connector must place CANH/CANL adjacent and keep protection/termination near the connector.

## Functional requirements

- With only the 24 V input and the CAN connector attached, the board shall pass bus traffic, read all four inputs and drive all four outputs.
- The MCU shall reach the bus only through the external transceiver; classical CAN and CAN-FD shall both be supported, and the maximum qualified data-phase rate stated.

## Power input and protection

- The continuous 24 V input range shall be stated, with every part in that path rated above it with margin.
- Reverse polarity at that magnitude shall not damage the board or latch, and transients shall be clamped below the rating of everything behind the input.
- Conversion to the logic rail(s) shall not dissipate the full input-to-output difference at load; the transceiver shall get the supply voltage its datasheet requires.

## CAN interface and termination

- CANH and CANL shall occupy adjacent connector contacts, with no other contact between them.
- Termination shall be a nominal 120 Ω differential load when enabled and switchable to fully removed without unsoldering parts.
- Bus protection shall meet the declared IEC 61000-4-2 level, be balanced line to line, and add no more capacitance than the qualified rate allows.
- The bus fault voltage withstood shall be stated and shall cover CANH or CANL shorted to ground or to the node's own 24 V.

## Digital inputs and low-side outputs

- Each input shall have a stated threshold and hysteresis and a defined state with its terminal open.
- Each input shall survive, continuously, any voltage from 0 V to the maximum rated 24 V input, in either polarity.
- Each output shall switch independently, be off from power-on until firmware drives it, and clamp inductive turn-off energy within its rating, at the stated per-channel current with all four on.

## Placement and layout

- Bus protection shall be first in the path from the connector contacts, termination immediately behind it, with no bus trace reaching elsewhere first.
- CANH/CANL shall be a coupled pair of constant spacing over an unbroken return path, with no stubs, and discharge return shall reach the connector's reference by a short, low-inductance path.

## Test and bring-up

- Programming and debug shall be on a labelled footprint usable with the board powered and the bus mated.
- Test points shall be provided on each rail, on CANH and CANL, and on the transceiver's TXD/RXD pair.

## Open choices

- MCU and transceiver selection, subject to an integrated CAN-FD controller, the I/O count above, and the declared rate and fault ratings.
- Whether termination switches manually or under MCU control, and the connector families and rail voltages that follow.
