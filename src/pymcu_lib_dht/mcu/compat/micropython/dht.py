# MicroPython-compatible dht module (DHT11 and DHT22/AM2302).
#
# The code below is the MicroPython API, unchanged:
#
#   from machine import Pin
#   from dht import DHT11, DHT22
#
#   sensor = DHT11(Pin(2))
#   sensor.measure()
#   sensor.humidity()      # uint16, tenths of %RH (real MicroPython: int %RH)
#   sensor.temperature()   # int16, tenths of C (real MicroPython: int/float C)
#
# Real MicroPython's DHT11 reports plain integers and its DHT22 reports one
# decimal digit; both are represented here in tenths so one pair of methods
# serves both models without a float (see docs/accuracy.md). Real MicroPython
# raises OSError on a failed measure(); PyMCU has no runtime exception
# payloads for that, so `measure()` instead records the outcome in `.failed`
# and leaves the last good reading in place. Check `.failed` after every
# measure() the way real MicroPython code checks the raised OSError.
from pymcu.types import uint8, uint16, int16, uint32, inline

from _dht.core import Frame, FRAME_ERROR
from _dht.decode import decode_dht11, decode_dht22

_START_LOW_DHT11_MS: uint16 = 18
_START_LOW_DHT22_MS: uint16 = 1


class DHT11:
    """A DHT11 read through a machine.Pin, MicroPython dht-module shaped."""

    @inline
    def __init__(self, pin):
        # machine.Pin carries the port name the HAL works in; taking it here is
        # what lets a MicroPython script hand us its own Pin object.
        self._frame = Frame(pin._name)
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
    """A DHT22/AM2302 read through a machine.Pin, same shape as DHT11."""

    @inline
    def __init__(self, pin):
        self._frame = Frame(pin._name)
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
        humidity, temperature = decode_dht22(frame)
        self._humidity = humidity
        self._temperature = temperature

    @inline
    def humidity(self) -> uint16:
        return self._humidity

    @inline
    def temperature(self) -> int16:
        return self._temperature


# DHT21/AM2301: identical protocol and byte layout to the DHT22 -- an alias,
# not a second implementation. See docs/sensors.md.
DHT21 = DHT22
