# Accuracy and limits

## What each sensor reports

See [Choosing a sensor](sensors.md) for the full comparison table (range, accuracy,
resolution, start signal, sample interval) across DHT11, DHT22 and DHT21.

The short version: the DHT11 reports plain integer %RH and integer C with no decimal
digit and no negative temperatures; the DHT22/DHT21 report one decimal digit and can go
below zero. `dht.py` and `compat/micropython/dht.py` report both in tenths (e.g. `653`
for 65.3%), so `.humidity()`/`.temperature()` always return the same type regardless of
model — a DHT11 reading is just a tenths value that always ends in zero.

## Why tenths, as an int

The alternative was returning `float` from every layer, matching what `adafruit_dht`
does upstream. Two isolated probes were compiled and measured on the emulator, each the
same 6-pin LED-threshold shape, differing only in whether `humidity()`/`temperature()`
carried the value as `int16` tenths or as `float`:

| Return type | Flash (code, excl. 104-byte vector table) |
|---|---|
| `int16` tenths | 140 bytes |
| `float` | 680 bytes |

Returning `float` costs **540 bytes more — about 4.9x** for this isolated comparison,
because AVR has no FPU: a `float` compare or divide pulls in `avr-libc`'s software
float routines, while an `int16`/`uint16` compare is a couple of native instructions.
On an ATmega328P's 32 KB that is a meaningful fraction of flash to spend on one decimal
digit a caller could get from a `divmod(value, 10)` instead — see the UART monitor
example, which prints tenths this way.

`dht.py` (native + MicroPython) and `compat/micropython/dht.py` both use `int16`
tenths for this reason, on both DHT11 and DHT22 — not just to save flash on the DHT11,
but so `.humidity()`/`.temperature()` have one return type regardless of which model is
attached, letting the same threshold-comparison code in an application work against
either sensor unchanged.

`adafruit_dht.py` is the one exception, and deliberately so: matching
`adafruit_dht`'s real upstream signature — `float`, always, even for the DHT11's
exact-tenth values — is the entire point of that module existing under that import
name. A CircuitPython script that already budgets for `adafruit_dht`'s cost gets the
real API; a script that cares about flash uses `dht` instead, at whatever module name
its own layer resolves.

## Read interval

The datasheets specify at least 1 second between DHT11 reads and at least 2 seconds
between DHT22/DHT21 reads; examples in this library use 2 seconds across the board for
margin. Reading faster than that returns unreliable data, not a driver error — nothing
here enforces the interval, since a fixed capacitor+delay constraint like this belongs
in the caller's own timing, not in a library that can't tell how the rest of the
program spends its time.

## Error reporting

`Frame.read()` returns `FRAME_ERROR` for three distinct failure conditions, and the
layers built on it do not distinguish between them at the API level:

1. The sensor never pulled the line low for the initial ACK (nothing connected, or
   powered but not yet ready — every model in the family needs roughly a second after
   power-up before its first read).
2. A bit-timing wait hit its 255-iteration timeout mid-read.
3. The checksum byte didn't match the four data bytes.

All three mean the same thing to a caller: this reading is not usable, try again after
the read interval. Splitting them into distinct error codes would let a caller
distinguish "sensor missing" from "one glitched bit," but nothing in this driver's
three call sites (native, MicroPython, CircuitPython) needs that distinction, and
each additional code is one more thing every architecture's `_dht_<arch>.py` has to
agree on and report correctly.

### The MicroPython and CircuitPython adapters differ here

Real MicroPython's `dht` module raises `OSError` from `.measure()` on a failed read;
real CircuitPython's `adafruit_dht` raises `RuntimeError` from the `.temperature` /
`.humidity` properties. PyMCU's runtime exception set is a fixed, small list —
`ValueError`, `TypeError`, `IndexError`, `KeyError`, `NotImplementedError`,
`ZeroDivisionError` — with no general `OSError` or `RuntimeError`, because there is no
OS and nothing "runs" outside what already type-checked at compile time.

- `dht.py` and `compat/micropython/dht.py` use the same `.failed` boolean flag the
  pre-existing `pymcu-micropython` DHT examples already used, rather than raising. A
  caller checks `sensor.failed` after `.measure()` instead of wrapping it in
  `try/except OSError`.
- `adafruit_dht.py` raises `ValueError` in place of `RuntimeError` — the nearest
  supported builtin — so `try/except ValueError:` still reads like the upstream idiom,
  just with the actual exception type PyMCU can raise.

Both are the smallest change that keeps the surrounding script looking like the API it
mirrors; see [Getting started](getting-started.md) for both in context.
