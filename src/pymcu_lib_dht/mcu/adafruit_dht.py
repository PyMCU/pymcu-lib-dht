# CircuitPython-compatible adafruit_dht module (DHT11 and DHT22/AM2302).
#
# The code below is the CircuitPython API, unchanged:
#
#   import board
#   from adafruit_dht import DHT11, DHT22
#
#   sensor = DHT11(board.D2)
#   print(sensor.temperature)   # property: triggers a fresh read
#   print(sensor.humidity)      # property: triggers a fresh read
#
# Real adafruit_dht always reports float degrees/percent, including the
# DHT11's exact-tenth values (e.g. 24.0) -- matching that upstream shape is
# the point of this module, so it is the one place in this library that
# returns float rather than the tenths-as-int shape dht.py uses (see
# docs/accuracy.md for why the other two layers avoid it).
#
# adafruit_dht raises RuntimeError on a failed read; PyMCU's exception set has
# no RuntimeError, so this raises ValueError instead -- the nearest supported
# builtin for "the value you asked for could not be produced".
#
# There is no compat/circuitpython/ copy of this file, and it would have
# nothing to do: PyMCU's CircuitPython layer ships no adafruit_dht of its own,
# so nothing shadows this module, and `board.Dn` constants are plain pin-name
# strings -- the same shape the constructor already takes. A copy under
# compat/ would only be a second place to fix the same bug.
from pymcu.types import uint8, uint32, inline

from _dht.core import Frame, FRAME_ERROR, START_LOW_DHT11_MS, START_LOW_DHT22_MS
from _dht.decode import decode_dht11, decode_dht22


class DHT11:
    """A sequence of one DHT11 reading, addressed like adafruit_dht.DHT11."""

    @inline
    def __init__(self, pin, use_pulseio: uint8 = 1):
        self._frame = Frame(pin)

    @property
    def temperature(self) -> float:
        frame: uint32 = self._frame.read(START_LOW_DHT11_MS)
        if frame == FRAME_ERROR:
            raise ValueError("DHT11 checksum did not validate, try again")
        humidity, temperature = decode_dht11(frame)
        return temperature / 10.0

    @property
    def humidity(self) -> float:
        frame: uint32 = self._frame.read(START_LOW_DHT11_MS)
        if frame == FRAME_ERROR:
            raise ValueError("DHT11 checksum did not validate, try again")
        humidity, temperature = decode_dht11(frame)
        return humidity / 10.0

    @inline
    def exit(self):
        pass


class DHT22:
    """A sequence of one DHT22 reading, addressed like adafruit_dht.DHT22."""

    @inline
    def __init__(self, pin, use_pulseio: uint8 = 1):
        self._frame = Frame(pin)

    @property
    def temperature(self) -> float:
        frame: uint32 = self._frame.read(START_LOW_DHT22_MS)
        if frame == FRAME_ERROR:
            raise ValueError("DHT22 checksum did not validate, try again")
        humidity, temperature = decode_dht22(frame)
        return temperature / 10.0

    @property
    def humidity(self) -> float:
        frame: uint32 = self._frame.read(START_LOW_DHT22_MS)
        if frame == FRAME_ERROR:
            raise ValueError("DHT22 checksum did not validate, try again")
        humidity, temperature = decode_dht22(frame)
        return humidity / 10.0

    @inline
    def exit(self):
        pass


# DHT21/AM2301: identical protocol and byte layout to the DHT22 -- an alias,
# not a second implementation. See docs/sensors.md.
DHT21 = DHT22
