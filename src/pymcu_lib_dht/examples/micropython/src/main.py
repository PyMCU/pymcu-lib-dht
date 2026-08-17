# DHT11 MicroPython example -- the MicroPython idiom, unchanged.
#
# Wiring (Arduino Uno):
#   DHT11 DATA -> D2  (PD2), 4.7 kohm pull-up to +5V recommended
#   DHT11 VCC  -> +5V
#   DHT11 GND  -> GND
#   LED: built-in on D13 (no wiring needed)
#
# humidity()/temperature() return tenths here (653 = 65.3%RH), not the plain
# integer real MicroPython's DHT11 reports -- see compat/micropython/dht.py.
from machine import Pin
from utime import sleep_ms
from dht import DHT11


def main():
    led = Pin(13, Pin.OUT)
    sensor = DHT11(Pin(2, Pin.IN))

    while True:
        sensor.measure()

        if sensor.failed:
            led.low()
        elif sensor.humidity() > 600:   # tenths of %RH
            led.high()
        else:
            led.low()

        sleep_ms(2000)
