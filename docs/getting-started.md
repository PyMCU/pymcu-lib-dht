# Getting started

## Install

```bash
cd your-pymcu-project
pymcu install dht
```

This adds `pymcu-lib-dht` to your project's dependencies and verifies its examples
build for your project's target chip before it's recorded as installed.

## Wire the sensor

DHT modules bought with a breakout board (three pins: `VCC`, `OUT`/`DATA`, `GND`)
already carry the pull-up resistor; a bare four-pin sensor needs a 4.7 kOhm resistor
between `DATA` and `VCC`. See [Wiring](wiring.md) for the full diagram — it's the same
across the whole family.

## Choose a sensor

DHT11 is cheaper and coarser (integer %RH and C, no negative temperatures). DHT22/AM2302
and DHT21/AM2301 report one decimal digit and can go below zero. See
[Choosing a sensor](sensors.md) for the full comparison.

## Read a value

Which module name and API you write against depends on the `stdlib` your project
declares in `pyproject.toml`, under `[tool.pymcu]`.

### Native (no `stdlib` layer declared) and MicroPython (`stdlib = ["micropython"]`)

Both use the module name `dht` — that's real MicroPython's own module name, and native
uses the same one on purpose (see `docs/index.md`).

```python
from dht import DHT11, DHT22   # DHT21 also available, an alias of DHT22

sensor = DHT11("PD2")          # native: a bare pin name

def main():
    sensor.measure()
    if sensor.failed:
        return   # timeout, or a bad checksum: try again later
    humidity = sensor.humidity()        # tenths of %RH, e.g. 653 = 65.3
    temperature = sensor.temperature()  # tenths of C, e.g. -55 = -5.5 (DHT22 only)
```

```python
from machine import Pin
from dht import DHT22

sensor = DHT22(Pin(2))         # MicroPython: a machine.Pin

def main():
    sensor.measure()
    if sensor.failed:
        return
    print(sensor.humidity(), sensor.temperature())
```

`.humidity()`/`.temperature()` return tenths as a plain `int`, not a `float` — see
[Accuracy and limits](accuracy.md#why-tenths-as-an-int) for the measured flash cost
that decision is based on. `.failed` exists instead of a raised exception because
real MicroPython's `OSError` has no PyMCU equivalent; see
[Accuracy and limits](accuracy.md#error-reporting).

### CircuitPython (`stdlib = ["circuitpython"]`)

```python
import board
from adafruit_dht import DHT22   # DHT21 also available, an alias of DHT22

sensor = DHT22(board.D2)

def main():
    try:
        print(sensor.temperature, sensor.humidity)   # floats, matching upstream
    except ValueError:
        pass
```

This mirrors `adafruit_dht.DHT11`/`DHT22`: `.temperature` and `.humidity` are
properties, reading either one triggers a fresh measurement, and both return `float` —
the one place in this library that does, because matching `adafruit_dht`'s real
signature is the entire point of this module.

## One name to avoid at module level

Until the compiler is fixed, a module-level global in your firmware whose name
matches a parameter inside a library silently wins over the parameter. A firmware
that declares `start_low_ms`, `mask`, `bit`, `count`, `frame`, `timeout`,
`expected` or `chksum` at module level changes what this driver does with no
diagnostic: a global `start_low_ms = 250` makes the start pulse 250 ms instead of
the 18 ms the DHT11 needs, measured on the emulator. Locals inside your functions
are fine, and so is any other name.

This is a compiler bug rather than something the library can protect itself from —
no set of parameter names is safe from every firmware — so it is pinned as a strict
xfail in `tests/test_timing.py` and will be removed here once it is fixed.

## Examples

Five complete example projects live in the repository (and travel in the sdist,
not the wheel), under `examples/`:

| Example          | API           | Sensor | What it does                                      |
|------------------|---------------|--------|----------------------------------------------------|
| `native`         | native        | DHT11  | Drives the built-in LED from a humidity threshold. |
| `native_dht22`   | native        | DHT22  | Lights the LED as a frost warning below 0.0 C.     |
| `micropython`    | MicroPython   | DHT11  | Same humidity threshold, `machine.Pin` idiom.      |
| `circuitpython`  | CircuitPython | DHT22  | Same frost-warning logic, `adafruit_dht` idiom.    |
| `uart-monitor`   | native        | DHT22  | Prints every reading over UART, tenths and sign.   |

Each is a real PyMCU project (its own `pyproject.toml` + `src/main.py`) and builds on
its own:

```bash
cd examples/native
pymcu build
```
