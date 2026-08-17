# DHT11 native example -- read and act on the value.
#
# Wiring (Arduino Uno):
#   DHT11 DATA -> D2  (PD2), 4.7 kohm pull-up to +5V recommended
#   DHT11 VCC  -> +5V
#   DHT11 GND  -> GND
#   LED: built-in on D13 (no wiring needed)
#
# The built-in LED lights while humidity is above 60% RH, and blinks fast on
# a read error (bad checksum or a sensor that never answered the start signal).
from pymcu.hal.gpio import Pin
from pymcu.time import delay_ms
from dht import DHT11


def main():
    led = Pin("PB5", Pin.OUT)
    sensor = DHT11("PD2")

    while True:
        sensor.measure()

        if sensor.failed:
            led.toggle()
            delay_ms(200)
            continue

        if sensor.humidity() > 600:   # tenths of %RH
            led.high()
        else:
            led.low()

        delay_ms(2000)
