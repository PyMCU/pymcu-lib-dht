# Model-specific decoding of a DHT-family 40-bit frame.
#
# `_dht_core.Frame.read()` hands back four raw data bytes packed into one
# uint32 (FRAME_ERROR already ruled out by the caller) -- what those bytes
# *mean* is a per-model decision, not a wire decision, which is why this file
# has no `match __CHIP__.arch` and never will: it is plain arithmetic on a
# value the core already fetched, identical on every architecture.
#
# Both models report in tenths, packed into plain integers rather than a
# float:
#
#   DHT11 -- 8-bit integer counts, no fractional resolution. b0 is %RH,
#            b2 is C; the decimal bytes b1/b3 are normally zero on genuine
#            sensors, so they are not read here (see docs/accuracy.md).
#            Multiplying the integer count by 10 reports it in the same
#            tenths unit DHT22 uses, so both models share one return shape.
#   DHT22 -- 16-bit values in tenths already: humidity is (b0:b1) unsigned;
#            temperature is (b2:b3) with the sign in bit 15 of that word and
#            the magnitude in the low 15 bits (datasheet section 4).
#
# Returning tenths as an int keeps every layer's arithmetic in whole
# registers -- no software float library pulled in just to report a digit
# that a caller can print with one divmod. See docs/accuracy.md for the flash
# measurement that backs this choice.
from pymcu.types import int16, uint8, uint16, uint32, inline


@inline
def _bytes(frame: uint32):
    b0: uint8 = (frame >> 24) & 0xFF
    b1: uint8 = (frame >> 16) & 0xFF
    b2: uint8 = (frame >> 8) & 0xFF
    b3: uint8 = frame & 0xFF
    return b0, b1, b2, b3


@inline
def decode_dht11(frame: uint32):
    b0, b1, b2, b3 = _bytes(frame)
    humidity: uint16 = b0 * 10
    temperature: int16 = b2 * 10
    return humidity, temperature


@inline
def decode_dht22(frame: uint32):
    b0, b1, b2, b3 = _bytes(frame)
    humidity: uint16 = (b0 << 8) | b1
    magnitude: int16 = ((b2 & 0x7F) << 8) | b3
    if b2 & 0x80:
        temperature: int16 = -magnitude
    else:
        temperature: int16 = magnitude
    return humidity, temperature
