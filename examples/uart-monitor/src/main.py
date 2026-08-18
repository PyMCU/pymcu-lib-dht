# DHT22 UART monitor -- prints every reading over UART (115200 baud).
#
# Wiring (Arduino Uno):
#   DHT22 DATA -> D2  (PD2), 4.7 kohm pull-up to +5V recommended
#   DHT22 VCC  -> +5V
#   DHT22 GND  -> GND
#
# UART output:
#   OK:    "H: 65.3  T: -5.5"
#   Error: "read error"
#
# humidity()/temperature() return tenths as a signed int, not a float (see
# docs/accuracy.md) -- printing one decimal digit is a divmod, not a float
# format. The minus sign goes out on its own `print` because the whole/tenths
# split below is computed on an unsigned magnitude, and because PyMCU has no
# runtime string objects: `sign = "-"` would be a `str` variable, which is not
# something the compiler can hold (see the language limitations page). The
# f-strings here are streamed straight to the UART, one write per piece.
from pymcu.time import delay_ms
from dht import DHT22


def main():
    sensor = DHT22("PD2")
    print("DHT22 ready")

    while True:
        sensor.measure()

        if sensor.failed:
            print("read error")
        else:
            h = sensor.humidity()
            print(f"H: {h // 10}.{h % 10}  T: ", end="")

            t = sensor.temperature()
            if t < 0:
                t = -t
                print("-", end="")
            print(f"{t // 10}.{t % 10}")

        delay_ms(2000)
