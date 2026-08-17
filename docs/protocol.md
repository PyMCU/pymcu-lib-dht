# The DHT protocol

DHT11, DHT22 (AM2302) and DHT21 (AM2301) all talk over the same single open-drain-style
data line, driven from both ends at different times, and all three send the same
40-bit frame shape: humidity high byte, humidity low byte, temperature high byte,
temperature low byte, and a checksum. That shared shape is why one AVR routine
(`_dht_avr.py`) and one exchange (`_dht_core.Frame`) serve the whole family — what
differs between the models is the start signal duration, and what the four data
bytes *mean*.

## The exchange, as `_dht_avr.py` implements it

1. **Start signal** — the MCU drives the line low, then releases it and lets the
   external pull-up bring it high. How long the MCU holds it low is the one part of
   the exchange that is a parameter, not a constant — see
   [Where the models diverge](#where-the-models-diverge) below.
2. **Sensor ACK** — the sensor pulls the line low for ~80 us, then high for ~80 us, to
   say "I heard you, here comes data." Identical across the family.
3. **40 data bits, MSB first** — each bit starts with a ~50 us LOW pulse (the same for
   every bit); what varies is the HIGH pulse that follows: ~26-28 us for a `0`, ~70 us
   for a `1`. Identical across the family — a DHT22 and a DHT11 send their bits with
   the same timing, only what the bits add up to differs.
4. **Checksum** — the low 8 bits of `b0 + b1 + b2 + b3` must equal the fifth byte, or
   the reading is discarded. Identical across the family.

## How the bit decode works in this driver

`_pd_wait(mask, level)` busy-waits for the line to reach `level`, counting down from a
255-iteration timeout; it returns 0 on timeout (treated as a read failure) and the
remaining count otherwise — the exact value isn't used, only whether it hit zero.

`_pd_byte(mask)` decodes one byte by, for each bit: waiting through the LOW pulse,
then counting loop iterations while the line stays HIGH, via `_pd_high_count()`. At
16 MHz that loop costs ~10.1 cycles/iteration in the compiled binary — measured on the
emulator (`tests/test_timing.py::TestBitDiscrimination`), not assumed — so a `0` bit
(26-28 us HIGH) produces roughly 41-45 counts and a `1` bit (70-75 us) produces
roughly 111-119: `HIGH_COUNT_THRESHOLD = 64` sits with wide margin on both sides, and
the longest `1` still lands well under the 255 a `uint8` counter can hold before it
saturates and stops climbing. This is a duration comparison done by counting, not a
timer capture, which is why the driver has no dependency on any timer peripheral: it
costs nothing beyond the pin itself.

`tests/test_timing.py` measures every timing-critical number on the emulator rather
than trusting a comment: the start-signal duration directly (`TestStartPulse` — the
AVR drives the pin, avr8sharp reads back how long DDRD/PORTD hold it low), the ACK/bit
wait budget directly (`TestEdgeWaiting` — it must outlast the ~80 us the sensor can
hold one level, or no reading ever completes), and the bit threshold indirectly
(`TestBitDiscrimination`), since avr8sharp's Python binding has no way to script a
virtual DHT reply back onto a pin the AVR is reading. Instead, `_pd_high_count()` is
calibrated by having the AVR drive its own pin HIGH and run the real counting loop
against it — the loop cannot tell a self-driven HIGH from a sensor-driven one, so this
measures the loop's actual cycle cost in the compiled binary, which the datasheet's 0/1
windows (and the counter's own saturation point) are then checked against.
`HIGH_COUNT_THRESHOLD` itself is read out of `_dht_avr.py`'s source rather than copied,
so a future change to the driver can't silently stop agreeing with its own test.

## Where the models diverge

| | DHT11 | DHT22 / AM2302 | DHT21 / AM2301 |
|---|---|---|---|
| Start signal (host holds LOW) | >= 18 ms | ~1 ms (18 ms also works, just slower) | same as DHT22 |
| Humidity bytes (b0:b1) | b0 = integer %RH, b1 normally 0 | 16-bit, tenths of %RH, unsigned | same as DHT22 |
| Temperature bytes (b2:b3) | b2 = integer C, b3 normally 0 | 16-bit: bit 15 = sign, bits 14-0 = tenths of C | same as DHT22 |
| Resolution | 1 %RH, 1 C | 0.1 %RH, 0.1 C | same as DHT22 |
| Negative temperature | Not representable | Real, and not two's complement — see below | same as DHT22 |

DHT21/AM2301 uses the exact same protocol and byte layout as the DHT22 — this
library exposes it as `DHT21 = DHT22`, an alias, rather than a duplicated
implementation that the two could drift apart from. See
[Choosing a sensor](sensors.md).

**The DHT22's negative encoding is a sign flag, not two's complement.** Bit 15 of the
temperature word is a sign bit; bits 14-0 are the plain magnitude in tenths of a
degree. `-6.9 C` is `1000 0000 0100 0101` (`0x8045`): sign bit set, magnitude
`0x0045` = 69. A decoder that sign-extends the 16-bit word instead of masking off bit
15 and negating separately reads that same frame as `+3277.3 C` (`0x8045` interpreted
as a two's-complement `int16`) — a value that is wrong by four orders of magnitude and
still parses as a plausible-looking number if nothing downstream range-checks it. See
`_dht_decode.decode_dht22` and `tests/test_dht.py::TestDecoding` for the code and the
worked datasheet example this guards.

## Where all three models agree

Everything not in the table above: the ACK sequence, the per-bit LOW/HIGH shape, the
checksum, and the 40-bit total frame length. `_dht_core.Frame.read(start_low_ms)`
takes the one thing that varies as a parameter and returns the same raw
`uint32` (four bytes packed MSB-first) or `FRAME_ERROR` regardless of which model is on
the other end of the wire — decoding what the bytes mean is left entirely to
`_dht_decode.py`, which never touches hardware and needs no chip dispatch of its own.

## Timing is not cycle-exact

Unlike WS2812 (see `pymcu-lib-neopixel`), the DHT family tolerates tens of
microseconds of jitter — the 0/1 threshold has margin on both sides even at 16 MHz.
`Frame.read()` does not disable interrupts. A short interrupt during the byte loop can
still corrupt one sample, but the checksum catches it and the caller sees a failed
read instead of a garbled value that looks plausible.

## Return value

`Frame.read(start_low_ms) -> uint32` packs the four data bytes MSB-first, or
`FRAME_ERROR` (`0xFFFFFFFF`) if the ACK never came, a bit-wait timed out, or the
checksum didn't match. No real reading can produce four bytes that are all `0xFF` —
humidity and temperature bytes are datasheet-bounded well under that on every model in
the family — so it is safe as a sentinel with no ambiguity against real data.
