# The family

Five names, two protocols' worth of difference between them, and one driver.

| Sold as | Same part as | Humidity | Temperature | Resolution | Class to use |
|---|---|---|---|---|---|
| DHT11 | — | 20–90% ±5% | 0–50 °C ±2 °C | 1 unit | `DHT11` |
| DHT22 | AM2302 | 0–100% ±2–5% | −40–80 °C ±0.5 °C | 0.1 unit | `DHT22` |
| AM2302 | DHT22 | as DHT22 | as DHT22 | 0.1 unit | `DHT22` |
| DHT21 | AM2301 | 0–100% ±3% | −40–80 °C ±0.5 °C | 0.1 unit | `DHT21` |
| AM2301 | DHT21 | as DHT21 | as DHT21 | 0.1 unit | `DHT21` |

`DHT21` is `DHT22` — a plain alias in `dht.py`, not a second implementation.
The parts are electrically and protocol-identical; only the accuracy printed
on the datasheet differs, and a driver cannot act on that.

## What actually differs on the wire

Almost nothing. All five use the same single-wire exchange: the host pulls the
line low to start, the sensor acknowledges, and then sends 40 bits where a bit's
value is the width of its high pulse (~26–28 µs for a zero, ~70 µs for a one).
`_dht/avr.py` implements that once.

Two things differ, and both are handled outside the timing code:

**How long the host holds the line low to start.** 18 ms for a DHT11, ~1 ms for
a DHT22/DHT21. This is a parameter of `dht_read()`, which is why picking the
wrong class is a real mistake rather than a cosmetic one — an 18 ms start is out
of spec for a DHT22, even though one will often still answer on the bench.

**What the four data bytes mean.** Not a wire difference at all, which is why it
lives in `_dht/decode.py` with no chip dispatch in sight:

- **DHT11** sends integer counts. Byte 0 is %RH, byte 2 is °C, and the two
  decimal bytes are zero on genuine parts. It cannot report a fraction and it
  cannot report a temperature below zero.
- **DHT22/DHT21** send tenths across two bytes. Humidity is a plain 16-bit
  value; temperature keeps its *sign in bit 15* and its magnitude in the low 15
  bits. It is not two's complement — a decoder that sign-extends reads −6.9 °C
  as 3277.3 °C and looks entirely plausible until it is below freezing.

Both models are reported in tenths by this library, so one pair of methods
serves the whole family without pulling in a software float. A DHT11 reading of
35% comes back as `350`. See [accuracy.md](accuracy.md).

## How often you can read one

Not as often as you would like, and the driver does not enforce it:

- **DHT11** — once per second.
- **DHT22/DHT21** — once every two seconds.

Reading faster does not fail cleanly; the sensor answers with its previous
measurement, or does not answer at all and the read times out. If a loop needs
to run faster than the sensor, keep the last good reading and measure on a
timer rather than every pass.

## What is not supported

- **Non-AVR targets.** The bit timing exists for AVR only. On any other
  architecture the library raises a `CompileError` at build time rather than
  returning a sentinel value — "it compiled" means "it is implemented". See
  [porting.md](porting.md).
- **Pins outside PD2–PD7.** Port D only, for now.
- **AM2320 and friends.** Those are I²C parts despite the family resemblance,
  and share none of this protocol.
