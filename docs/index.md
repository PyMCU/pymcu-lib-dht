# pymcu-lib-dht

A DHT-family temperature & humidity sensor driver for PyMCU — DHT11, DHT22/AM2302, and
DHT21/AM2301 — Python source the compiler reads at build time and turns into machine
code, ahead of time. There is no interpreter on the chip — a `sensor.measure()` call
compiles down to the same 1-wire bit-banging you'd hand-write in C.

## Pages

- [Getting started](getting-started.md) — install the library, wire a sensor, read
  a value in all three supported APIs.
- [Choosing a sensor](sensors.md) — DHT11 vs. DHT22 vs. DHT21, and which to buy.
- [The DHT protocol](protocol.md) — the shared 40-bit exchange this driver implements,
  where the models diverge, and how the timing decode is measured rather than assumed.
- [Wiring](wiring.md) — pins, pull-up resistor, power.
- [Accuracy and limits](accuracy.md) — what each sensor can and cannot tell you, and
  the measured flash cost behind why most of this driver avoids `float`.
- [Porting to a new architecture](porting.md) — what a new `_dht_<arch>.py` needs to
  provide.

## Layout

```
examples/                       five compilable projects -- sdist, not wheel
tests/
src/pymcu_lib_dht/
  __init__.py                   an ordinary Python package
  pymcu.toml                    the manifest
  mcu/                          everything the compiler reads, and only this
    dht.py                      native API, and MicroPython's own module name
    adafruit_dht.py             CircuitPython API (adafruit_dht shape)
    _dht/
      core.py                   the only file that dispatches on __CHIP__
      avr.py                    AVR bit-banging, one routine for the family
      decode.py                 per-model byte decoding, no chip dispatch
    compat/micropython/dht.py   machine.Pin constructor, same dht-module shape
```

Only `mcu/` goes on the compiler's include path, so `dht`, `adafruit_dht` and `_dht`
are the three top-level names this library claims and nothing else in the wheel is
reachable from a firmware. The implementation is a package rather than a set of
`_dht_*.py` modules because that path is flat and shared with every other installed
library: a bare `core.py` would be a global name, `_dht/core.py` is not.

`_dht/core.py` is the seam: it is the one file that knows what a chip is. Every public
module — `dht.py`, `adafruit_dht.py`, `compat/micropython/dht.py`, and
`_dht/decode.py` — is plain Python written against the API it mirrors (or, for
`_dht/decode.py`, against the raw frame `_dht.core.Frame` already fetched), with zero
architecture conditionals. That is what lets a MicroPython or CircuitPython script drop
in unchanged: it was never PyMCU-specific in the first place.

## Two module names, one driver

`dht` (native and MicroPython) and `adafruit_dht` (CircuitPython) both resolve to the
same underlying `Frame`/`_dht.decode` pair — see [Getting started](getting-started.md)
for which name your project's declared `stdlib` layer resolves, and
`docs/porting.md` for why `adafruit_dht` needs no `compat/circuitpython/` override
while `dht` needs one for MicroPython's `machine.Pin` constructor.
