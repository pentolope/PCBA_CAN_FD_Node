# PCBA_CAN_FD_Node — CAN-FD Sensor/Control Node

**Benchmark ID:** 06  
**Difficulty:** 2/5  
**Brief detail:** 3/5  
**Category:** industrial-network  
**Likely layer count:** 2 or 4  
**Primary stressors:** CAN differential pair, 24V input protection, termination, MCU clocking

## Design brief

Design a general-purpose CAN-FD node for a 24 V industrial system. Use a modern MCU with CAN-FD, an external CAN-FD transceiver, switchable 120-ohm termination, ESD protection at the bus connector, reverse-polarity and transient protection on the 24 V input, and an efficient local regulator. Provide four digital inputs and four low-side outputs for demonstration loads. The CAN connector must place CANH/CANL adjacent and keep protection/termination near the connector.

## Benchmark intent

This brief is intentionally one member of a heterogeneous PCBA-autodesign benchmark. Treat stated requirements as authoritative; where the brief leaves choices open, make and document reasonable engineering decisions rather than inventing hidden user requirements. The repository should remain a consumer of the shared `PCBA_AutoDesignAndTest` toolkit rather than accumulating board-specific logic in the toolkit.
