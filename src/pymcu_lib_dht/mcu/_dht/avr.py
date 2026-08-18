# DHT-family AVR implementation for ATmega328P at 16 MHz.
# Pattern mirrors _neopixel_avr.py.
#
# Extracted from PyMCU's stdlib driver (lib/src/pymcu/drivers/_dht11/avr.py):
# same bit-banging routine, just moved out from under pymcu.chips.atmega328p
# imports that only existed inside the monorepo tree, and generalised to a
# caller-supplied start-signal duration so one routine serves the whole family.
from pymcu.types import uint8, uint16, uint32, inline
from pymcu.chips.atmega328p import DDRD, PORTD, PIND
from pymcu.time import delay_ms, delay_us

from _dht.core import FRAME_ERROR

# Counts, not microseconds: see _pd_byte.
HIGH_COUNT_THRESHOLD: uint8 = 64


@inline
def dht_read(pin_name: str, start_low_ms: uint16) -> uint32:
    # Same if/elif pattern as pin_set_mode/pin_high in the stdlib GPIO HAL.
    # IRGenerator constant-folds string ID comparisons -- only the matching
    # branch survives, identical to how all GPIO HAL dispatch works.
    if pin_name == "PD2":
        return _pd_read(2, start_low_ms)
    elif pin_name == "PD3":
        return _pd_read(3, start_low_ms)
    elif pin_name == "PD4":
        return _pd_read(4, start_low_ms)
    elif pin_name == "PD5":
        return _pd_read(5, start_low_ms)
    elif pin_name == "PD6":
        return _pd_read(6, start_low_ms)
    elif pin_name == "PD7":
        return _pd_read(7, start_low_ms)
    return FRAME_ERROR


def _pd_read(bit: uint8, start_low_ms: uint16) -> uint32:
    mask: uint8 = 1 << bit

    # 1. Start signal -- drive LOW for start_low_ms (18 ms for DHT11, ~1 ms
    #    is enough for DHT22/DHT21, but the DHT11 duration works for either).
    DDRD.value  = DDRD.value  | mask
    PORTD.value = PORTD.value & ~mask
    delay_ms(start_low_ms)

    # 2. Release + pull-up
    DDRD.value  = DDRD.value  & ~mask
    PORTD.value = PORTD.value | mask
    delay_us(40)

    # 3. Sensor ACK
    if _pd_wait(mask, 0) == 0:
        return FRAME_ERROR
    if _pd_wait(mask, 1) == 0:
        return FRAME_ERROR

    # 4. Read 5 bytes: two data words (humidity, temperature) and a checksum.
    #    What the bits inside b0..b3 mean (plain counts vs. tenths, where a
    #    sign lives) is decided in _dht/decode.py, not here.
    b0: uint8 = _pd_byte(mask)
    b1: uint8 = _pd_byte(mask)
    b2: uint8 = _pd_byte(mask)
    b3: uint8 = _pd_byte(mask)
    chksum: uint8 = _pd_byte(mask)

    expected: uint8 = (b0 + b1 + b2 + b3) & 0xFF
    if chksum != expected:
        return FRAME_ERROR

    # An all-zero frame passes the checksum -- 0+0+0+0 == 0 -- so a line that
    # dies after a good ACK reports 0% humidity and 0 C as a valid reading. No
    # sensor in this family can measure 0% relative humidity, so a zero
    # humidity word is the transfer failing, not the air being dry. Zero
    # temperature is left alone: that one is a real reading.
    if b0 == 0 and b1 == 0:
        return FRAME_ERROR

    frame: uint32 = b0
    frame = (frame << 8) | b1
    frame = (frame << 8) | b2
    frame = (frame << 8) | b3
    return frame


def _pd_high_count(mask: uint8) -> uint8:
    # How long the line stays high, in loop iterations. A separate function so
    # a probe can drive it with the pin held high and measure what one
    # iteration costs -- the number that decides whether a bit reads as 0 or 1.
    count: uint8 = 0
    while PIND.value & mask:
        count = count + 1
        if count == 255:
            break
    return count


@inline
def _pd_wait(mask: uint8, level: uint8) -> uint8:
    timeout: uint8 = 255
    while timeout > 0:
        current: uint8 = PIND.value & mask
        if level == 0:
            if current == 0:
                return timeout
        else:
            if current:
                return timeout
        timeout = timeout - 1
    return 0


def _pd_byte(mask: uint8) -> uint8:
    result: uint8 = 0
    bit: uint8 = 0
    while bit < 8:
        if _pd_wait(mask, 0) == 0:
            return 0
        if _pd_wait(mask, 1) == 0:
            return 0
        count: uint8 = _pd_high_count(mask)
        result = result << 1
        # A bit's value is the length of its HIGH pulse, counted by the loop
        # above rather than timed: ~26-28 us means 0, ~70 us means 1. How many
        # counts that comes to depends on how many cycles the compiler spends
        # per iteration, which is why HIGH_COUNT_THRESHOLD is not a number
        # chosen by reading the code -- tests/test_timing.py drives the loop on
        # the emulator, converts the measured cycles into what a real sensor
        # would produce, and fails if either bit value lands near the
        # threshold. This encoding is the same for every sensor in the family;
        # only the start signal above varies by model.
        if count > HIGH_COUNT_THRESHOLD:
            result = result | 1
        bit = bit + 1
    return result
