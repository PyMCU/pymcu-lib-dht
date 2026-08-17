# DHT22 CircuitPython example -- the adafruit_dht idiom, unchanged.
#
# Wiring (Arduino Uno):
#   DHT22 DATA -> D2  (4.7 kohm pull-up to +5V recommended)
#   DHT22 VCC  -> +5V
#   DHT22 GND  -> GND
#   LED: board.LED (built-in, no wiring needed)
import board
import time
from digitalio import DigitalInOut, Direction
from adafruit_dht import DHT22


def main():
    led = DigitalInOut(board.LED)
    led.direction = Direction.OUTPUT
    sensor = DHT22(board.D2)

    while True:
        try:
            # Real adafruit_dht.temperature is float and negative below 0 C,
            # unchanged here -- the frost warning below reads the same way it
            # would against a real Feather with a real DHT22.
            led.value = sensor.temperature < 0.0
        except ValueError:
            led.value = False
        time.sleep(2.0)
