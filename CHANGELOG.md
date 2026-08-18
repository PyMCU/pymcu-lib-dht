# Changelog

## 0.1.1 — 2026-08-18

Built and measured against `pymcu-compiler` 0.1.0a10 on `pymcu-stdlib` 0.1.0a5.
All five examples compile for `arduino_uno`, and the decode, timing and UART
suites are green. The public API is unchanged — `api-surface.lock` is the same
hash it was in 0.1.0.

### Fixed

- **The UART monitor printed the character code of its minus sign.** It held the
  sign in a plain `str` local, and PyMCU has no runtime string objects to put one
  in; the compiler accepted it without a word and streamed `45` instead, so a
  reading of −5.5 °C went out as `T: 455.5`. The sign now goes out on its own
  `print`, and each reading is formatted with streamed f-strings rather than a
  nine-argument `print(..., sep="")` — which also takes the example from 3016 to
  1818 bytes of flash. This was wrong in 0.1.0 and nothing in the suite was
  looking at the output.
- **CI built no examples at all.** The loop still globbed
  `src/pymcu_lib_dht/examples/*/`, where they lived before 0.1.0 moved them to the
  repository root, so it matched nothing and the step passed. An empty glob now
  fails it.

### Changed

- `tests/test_uart.py` reads the serial port on the emulator: the formatting of a
  reading, on the values that break a naive formatter (a magnitude of exactly
  1000, a zero, and a tenth below zero), and the shipped example's own error path.
- The forward declarations ahead of every `humidity, temperature = decode_*(frame)`
  are gone; the compiler types the targets from the callee's return. Identical
  code generation bar one fewer frame slot, and 4 bytes off the native, MicroPython
  and CircuitPython examples.
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
- **A module-level global can still take over a parameter of a plain function.**
  0.1.0a10 fixed this for `@inline` parameters, which is most of this driver. It is
  still open for parameters of a plain `def`, which leaves three names exposed here:
  a firmware declaring `start_low_ms` drives the start pulse for that many
  milliseconds instead of 18, and one declaring `bit` (or `mask`) makes the driver
  bit-bang a pin nobody asked for. Locals are unaffected either way — a global named
  `count`, `chksum` or `expected` changes nothing, and that boundary is measured
  rather than assumed. It is a compiler bug and not one a library can protect itself
  from by choosing different names, so it is pinned as a strict xfail in
  `tests/test_timing.py` and will fail the day it is fixed. See
  [docs/getting-started.md](docs/getting-started.md#three-names-to-avoid-at-module-level).
- **Pins PD2–PD7 only**, and the AM2320 family is a different (I²C) part despite
  the name.

## 0.1.0 — 2026-08-17

First release. DHT11, DHT22/AM2302 and DHT21/AM2301 on AVR, through three APIs
over one driver: the native `dht` module, MicroPython's own `dht` shape, and
CircuitPython's `adafruit_dht`.
