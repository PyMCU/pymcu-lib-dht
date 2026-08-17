# Porting to a new architecture

`_dht_core.py` is the only file that dispatches on `__CHIP__`. Adding a new
architecture means adding one `case` to its `match __CHIP__.arch:` and writing the
module that case imports from — nothing in `dht.py`, `adafruit_dht.py`,
`compat/micropython/dht.py`, or `_dht_decode.py` changes, since none of them know what
a chip is.

## What to write

A new `_dht_<arch>.py`, exposing one function:

```python
def dht_read(pin_name: str, start_low_ms: uint16) -> uint32:
    ...
```

Its contract, taken from `_dht_avr.py`:

- `pin_name` is whatever string your architecture's GPIO HAL uses to name a pin (on
  AVR, register-relative names like `"PD2"`).
- `start_low_ms` is how long to hold the line low to start the exchange — the caller
  (`dht.py`, `compat/micropython/dht.py`, `adafruit_dht.py`) passes 18 for DHT11 and 1
  for DHT22/DHT21; your implementation should not hardcode a duration, since one
  routine has to serve every model in the family.
- Return the four data bytes packed MSB-first into a `uint32` (humidity hi, humidity
  lo, temperature hi, temperature lo) on a good read.
- Return `FRAME_ERROR` (`0xFFFFFFFF`) on any failure: ACK timeout, bit-wait timeout, or
  checksum mismatch. See [Accuracy and limits](accuracy.md#error-reporting) for why the
  three don't need to be distinguished.
- What the four bytes *mean* — plain integer counts, or 16-bit tenths with a sign bit —
  is not this function's concern. That decoding lives in `_dht_decode.py`, which is
  architecture-independent and needs no changes for a new port.
- The whole exchange (~20 ms worst case) happens inside this one call — there is
  no async/interrupt-driven variant to support, since a caller who does not want to
  block for that long should not be calling this at all.

## Wiring it into `_dht_core.py`

```python
match __CHIP__.arch:
    case "avr":
        from _dht_avr import dht_read
        return dht_read(self._pin, start_low_ms)
    case "your_arch":
        from _dht_your_arch import dht_read
        return dht_read(self._pin, start_low_ms)
    case _:
        raise CompileError("DHT timing is only implemented for AVR")
```

The `case _:` branch **must** raise `CompileError`. `pymcu lint --library` enforces
this (`sentinel-default` check): a default branch that returns something instead of
raising would compile on every architecture and only fail on the bench, silently,
long after the "supported" claim in `pymcu.toml` stopped being true.

## `adafruit_dht.py` lives at the package root only

`compat/micropython/dht.py` is a real override: the native and MicroPython shapes of
`dht` genuinely differ, in that one takes a pin name and the other takes a
`machine.Pin`. `adafruit_dht` has no such counterpart. PyMCU's CircuitPython layer
ships no `adafruit_dht` of its own, so nothing shadows the root module, and `board.Dn`
constants are plain pin-name strings -- the same shape the root file already takes.

An earlier version of this library kept a byte-for-byte copy under
`compat/circuitpython/`, on the reasoning that it made `supports.adapters` truer and
gave the API-surface check two real files to walk. Neither held up: the copy resolved
ahead of nothing but itself, so no build behaved differently for having it, and it
added a second place to fix any bug in a 75-line driver. If you are adding an adapter,
add one only where the API actually differs.

## Update the manifest

Add the new arch to `supports.arch` in `pymcu.toml`, and bump the distribution
version (the manifest itself carries no version — see `pymcu.toml`'s header comment
in `_dht_core.py`'s sibling files for why).

## Verify

```bash
pymcu lint --library src/pymcu_lib_dht
```

Then confirm both directions: every example still builds for AVR, and copying an
example with `target = "your_arch"` in `[tool.pymcu]` now builds too for DHT11 and
DHT22, instead of raising `CompileError`. If your architecture's timing differs enough
to be worth double-checking, see `tests/test_timing.py` for the pattern this library
uses to measure (rather than assert) the start pulse and bit-decode threshold on the
AVR emulator.
