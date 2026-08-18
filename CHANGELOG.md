# Changelog

## 0.1.1 — 2026-08-18

Built and measured against `pymcu-compiler` 0.1.0a10 on `pymcu-stdlib` 0.1.0a5.
All five examples compile for `arduino_uno`, and the decode, timing and UART
suites are green. The public API is unchanged — `api-surface.lock` is the same
hash it was in 0.1.0.

Flash for the five examples on `atmega328p`, both releases compiled with the same
0.1.0a10 compiler so the figures are comparable:

| Example | 0.1.0 | 0.1.1 |
|---|---:|---:|
| `native` | 990 | 990 |
| `native_dht22` | 1018 | 1010 |
| `micropython` | 974 | 974 |
| `circuitpython` | 1718 | 1714 |
| `uart-monitor` | 2996 | 1796 |

### Fixed

- **The UART monitor printed the character code of its minus sign.** It held the
  sign in a plain `str` local, and PyMCU has no runtime string objects to put one
  in; the compiler accepted it without a word and streamed `45` instead, so a
  reading of −5.5 °C went out as `T: 455.5`. The sign now goes out on its own
  `print`, and each reading is formatted with streamed f-strings rather than a
  nine-argument `print(..., sep="")` — which also takes the example from 2996 to
  1796 bytes of flash. This was wrong in 0.1.0 and nothing in the suite was
  looking at the output.
- **CI built no examples at all.** The loop still globbed
  `src/pymcu_lib_dht/examples/*/`, where they lived before 0.1.0 moved them to the
  repository root, so it matched nothing and the step passed. An empty glob now
  fails it.

### Changed

- `tests/test_uart.py` reads the serial port on the emulator: the formatting of a
  reading, on the values that break a naive formatter (a magnitude of exactly
  1000, a zero, and a tenth below zero), and the shipped example's own error path.
- `tests/test_timing.py` now also compiles a firmware whose module-level globals
  collide with every name this driver uses internally, and measures that the start
  pulse is still the one the driver asked for. Up to 0.1.0a9 it was not: a global
  `start_low_ms = 250` stretched the pulse to 250 ms, and a global `bit = 7` sent
  the driver to PD7 whatever pin the firmware named, so the sensor was never
  addressed at all. Both were reported from this library and fixed in the compiler
  for 0.1.0a10 — first for `@inline` parameters, then for plain ones. A library's
  parameter names are ordinary words, so this stays as a test.
- The forward declarations ahead of every `humidity, temperature = decode_*(frame)`
  are gone; the compiler types the targets from the callee's return. Same
  instructions, one fewer frame slot.
- `FRAME_ERROR` and the two start-signal durations (18 ms for a DHT11, 1 ms for a
  DHT22) each live in exactly one file now instead of two and three. Firmware is
  byte-identical on all five examples.
- The CPython suite loads the real `_dht/core.py` and scripts only `Frame.read()`,
  so the start-signal test measures the driver's own durations rather than a copy
  the suite made up.

### Known limitations

- **AVR only.** `_dht/core.py` raises a `CompileError` on any other architecture
  rather than returning something that looks like a reading. That error now points
  at the caller's own line even when the call sits under runtime control flow,
  which is new in the 0.1.0a10 compiler. Ports are welcome: `_dht/avr.py` is the
  whole contract and `_dht/decode.py` needs no changes for one.
- **Needs `pymcu-compiler` 0.1.0a10.** On 0.1.0a9 a firmware's module-level global
  took over a library parameter of the same name, which reached this driver through
  `start_low_ms`, `bit` and `mask` — see the note under *Changed*. The suite skips
  that check with a reason on an older compiler rather than failing, but the driver
  itself is only correct on 0.1.0a10.
- **Pins PD2–PD7 only**, and the AM2320 family is a different (I²C) part despite
  the name.

## 0.1.0 — 2026-08-17

First release. DHT11, DHT22/AM2302 and DHT21/AM2301 on AVR, through three APIs
over one driver: the native `dht` module, MicroPython's own `dht` shape, and
CircuitPython's `adafruit_dht`.
