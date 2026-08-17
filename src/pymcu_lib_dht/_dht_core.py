# DHT-family core -- the single-wire read every API layer sits on.
#
# This is the only file in the library that knows what a chip is. Every public
# module -- dht.py, adafruit_dht.py, and the compat/micropython adapter -- is
# written against `Frame` and stays free of architecture dispatch, so each one
# reads like the API it mirrors.
#
# Protocol: 1-wire, 40 bits (humidity hi/lo, temperature hi/lo, checksum). The
# only thing that differs between DHT11, DHT22 and DHT21 at this level is how
# long the host holds the line low to start an exchange -- the ACK, the 40-bit
# shape and the bit timing are identical across the family, so `start_low_ms`
# is a parameter here rather than three copies of this file. What the four
# data bytes *mean* (integer counts vs. tenths, where the sign bit lives) is a
# model decision, not a wire decision, and lives in `_dht_decode.py` instead.
from pymcu.chips import __CHIP__
from pymcu.exceptions import CompileError
from pymcu.types import uint16, uint32, inline

# Both bytes 0xFF forever: no real DHT reading can produce this. Humidity and
# temperature magnitude bytes are datasheet-bounded well under 0xFF (DHT22
# tops out around 1000 in its 15-bit magnitude, i.e. 0x03E8), and the checksum
# would have to independently agree with four bytes that can't occur -- so
# this is safe as a sentinel with no ambiguity against real data.
FRAME_ERROR: uint32 = 0xFFFFFFFF


class Frame:
    """A pin driving a DHT-family sensor, one raw 40-bit reading at a time."""

    @inline
    def __init__(self, pin: str):
        self._pin = pin

    @inline
    def read(self, start_low_ms: uint16) -> uint32:
        # uint32: the four data bytes packed MSB-first (humidity hi, humidity
        # lo, temperature hi, temperature lo); FRAME_ERROR on timeout or a
        # checksum mismatch. Decoding what the bytes mean is the caller's job.
        match __CHIP__.arch:
            case "avr":
                from _dht_avr import dht_read
                return dht_read(self._pin, start_low_ms)
            case _:
                # One string literal, not two adjacent ones: the parser reads a
                # single literal here and implicit concatenation is not part of
                # the accepted subset.
                raise CompileError("DHT timing is only implemented for AVR")
