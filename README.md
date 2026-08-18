# pymcu-lib-dht

DHT-family temperature & humidity sensor driver for [PyMCU](https://pymcu.org) — DHT11,
DHT22/AM2302, and DHT21/AM2301 — compiled to native machine code, with no interpreter
on the chip.

```bash
pymcu install dht
```

## Two module names, three APIs, one driver

Which module name and shape you get depends on the `stdlib` layer your project
declares. Native and MicroPython both import from `dht` — that is real MicroPython's
own module name; CircuitPython imports from `adafruit_dht`, matching that ecosystem's
real name instead.

**Native** (`stdlib` unset):

```python
from dht import DHT11, DHT22   # DHT21 is also available: an alias of DHT22

sensor = DHT22("PD2")
sensor.measure()
humidity = sensor.humidity()        # uint16, tenths of %RH: 653 = 65.3
temperature = sensor.temperature()  # int16, tenths of C: -55 = -5.5
```

**MicroPython** (`stdlib = ["micropython"]`) — a MicroPython script, unchanged:

```python
from machine import Pin
from dht import DHT11

sensor = DHT11(Pin(2))
sensor.measure()
print(sensor.humidity(), sensor.temperature())
```

**CircuitPython** (`stdlib = ["circuitpython"]`) — an `adafruit_dht` script, unchanged:

```python
import board
from adafruit_dht import DHT22

sensor = DHT22(board.D2)
print(sensor.temperature, sensor.humidity)   # float, matching upstream
```

None of those files contains a single `match __CHIP__.arch`: the layer adapters are
plain Python written against each API as it is documented upstream. Everything that has
to know about a chip lives in one private module, `_dht.core`, and the compiler folds
it away; everything that has to know what a byte *means* for a given sensor model lives
in `_dht.decode`, which needs no chip dispatch of its own.

## DHT11 vs. DHT22 vs. DHT21

- **DHT11** — integer %RH and C, no fractional resolution, no negative temperatures.
  Cheapest, and the smallest to compile against (see below).
- **DHT22/AM2302** — one decimal digit, negative temperatures, wider and more accurate
  range.
- **DHT21/AM2301** — the same protocol and byte layout as the DHT22. This library
  exposes it as `DHT21 = DHT22`, a plain alias, not a second implementation.

See `docs/sensors.md` for the full comparison and `docs/protocol.md` for the byte-level
differences.

## Cost

The whole driver is `@inline`: no object is allocated on the device, and a read
compiles down to the bit-banging routine at the call site (or a single shared
subroutine where the compiler's outliner judges that cheaper). Nothing is held in
SRAM between reads.

`dht.py` and `compat/micropython/dht.py` report tenths as a plain `int16`/`uint16`
rather than a `float`, on both DHT11 and DHT22: two isolated probes measured on the
emulator put a `float`-returning driver at 4.9x the flash of an `int16`-tenths one
(680 vs. 140 bytes) for the same logic. See `docs/accuracy.md` for the measurement.
`adafruit_dht.py` is the one exception — it matches `adafruit_dht`'s real `float`
signature on purpose, since fidelity to that upstream API is the point of the module.

Measured figures per chip are published in the
[library index](https://libraries.pymcu.org/index.json).

## Supported hardware

The whole DHT family on **AVR** (ATmega328P and friends), data line on `PD2`-`PD7`.
Timing is measured on the AVR emulator rather than assumed — see
`tests/test_timing.py` for the start-signal and bit-decode-threshold checks.

Other architectures raise a compile-time error rather than returning something that
looks like it worked. Ports are welcome: `_dht/avr.py` is the whole contract, and
`_dht/decode.py` (the per-model byte decoding) needs no changes for a new port.

One caveat that is the compiler's rather than this driver's: a **module-level global
in your firmware whose name matches a parameter inside a library wins over the
parameter**, with no diagnostic. A firmware that declares `start_low_ms` at module
level changes the start pulse this driver sends. See
[docs/getting-started.md](docs/getting-started.md#one-name-to-avoid-at-module-level)
for the full list of names and the measurement.

See `docs/` for the wire protocol, wiring diagrams, accuracy limits, sensor comparison,
and a porting guide for a new architecture.

## License

MIT.
