# DHT-family temperature & humidity sensors -- native PyMCU API, and the
# same module name real MicroPython's own `dht` package uses.
#
#   from dht import DHT11, DHT22
#
#   sensor = DHT11("PD2")        # compile-time pin binding
#   sensor.measure()             # one bus exchange (~20 ms)
#   sensor.humidity()            # uint16, tenths of %RH  (653 = 65.3%)
#   sensor.temperature()         # int16, tenths of C     (-55 = -5.5 C)
#
# `.measure()` / `.humidity()` / `.temperature()` is real MicroPython's own
# `dht` module shape. Native and MicroPython share this module name and this
# API on purpose -- the only thing that differs between them is how the
# constructor takes its pin (see compat/micropython/dht.py). CircuitPython
# uses a different module and a different (property) shape, matching
# `adafruit_dht` instead; see adafruit_dht.py.
#
# Values are returned in tenths rather than a float: DHT22 needs one decimal
# digit and a sign, and integer tenths give both without pulling in a
# software float library. See docs/accuracy.md for the measured flash cost
# that this choice is based on.
#
# DHT21/AM2301 uses the exact same protocol and byte layout as the DHT22 --
# it is an alias below, not a second implementation to keep in sync.
from pymcu.types import uint8, uint16, int16, uint32, inline

from _dht_core import Frame, FRAME_ERROR
from _dht_decode import decode_dht11, decode_dht22

_START_LOW_DHT11_MS: uint16 = 18
_START_LOW_DHT22_MS: uint16 = 1


class DHT11:
    """A DHT11 read through a bare pin name, MicroPython dht-module shaped."""

    @inline
    def __init__(self, pin: str):
        self._frame = Frame(pin)
        self.failed: uint8 = 0
        self._humidity: uint16 = 0
        self._temperature: int16 = 0

    @inline
    def measure(self):
        frame: uint32 = self._frame.read(_START_LOW_DHT11_MS)
        if frame == FRAME_ERROR:
            self.failed = 1
            return
        self.failed = 0
        humidity: uint16
        temperature: int16
        humidity, temperature = decode_dht11(frame)
        self._humidity = humidity
        self._temperature = temperature

    @inline
    def humidity(self) -> uint16:
        return self._humidity

    @inline
    def temperature(self) -> int16:
        return self._temperature


class DHT22:
    """A DHT22/AM2302 read through a bare pin name, same shape as DHT11."""

    @inline
    def __init__(self, pin: str):
        self._frame = Frame(pin)
        self.failed: uint8 = 0
        self._humidity: uint16 = 0
        self._temperature: int16 = 0

    @inline
    def measure(self):
        frame: uint32 = self._frame.read(_START_LOW_DHT22_MS)
        if frame == FRAME_ERROR:
            self.failed = 1
            return
        self.failed = 0
        humidity: uint16
        temperature: int16
        humidity, temperature = decode_dht22(frame)
        self._humidity = humidity
        self._temperature = temperature

    @inline
    def humidity(self) -> uint16:
        return self._humidity

    @inline
    def temperature(self) -> int16:
        return self._temperature


# DHT21/AM2301: identical protocol and byte layout to the DHT22 (see
# docs/sensors.md) -- a plain alias, not a second implementation.
DHT21 = DHT22
