# DHT22 native example -- the same module as DHT11 (dht.py), the sensor with
# tenths resolution and a negative temperature to handle.
#
# Wiring (Arduino Uno):
#   DHT22 DATA -> D2  (PD2), 4.7 kohm pull-up to +5V recommended
#   DHT22 VCC  -> +5V
#   DHT22 GND  -> GND
#   LED: built-in on D13 (no wiring needed)
#
# The built-in LED lights as a frost warning whenever the reading is below
# 0.0 C -- `temperature()` is a signed tenths-of-a-degree int16, so "below
# zero" is just `< 0`, the same comparison that would be wrong on the DHT11's
# unsigned byte and does not need one on this sensor either.
from pymcu.hal.gpio import Pin
from pymcu.time import delay_ms
from dht import DHT22


def main():
    led = Pin("PB5", Pin.OUT)
    sensor = DHT22("PD2")

    while True:
        sensor.measure()

        if sensor.failed:
            led.toggle()
            delay_ms(200)
            continue

        if sensor.temperature() < 0:   # tenths of C, signed
            led.high()
        else:
            led.low()

        delay_ms(2000)
