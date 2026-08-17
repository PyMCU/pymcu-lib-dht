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
# format, and the sign needs handling by hand since the whole/tenths split
# below is always computed on an unsigned magnitude.
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
            h_whole = h // 10
            h_frac = h % 10

            t = sensor.temperature()
            if t < 0:
                t = -t
                t_sign = "-"
            else:
                t_sign = ""
            t_whole = t // 10
            t_frac = t % 10

            print("H: ", h_whole, ".", h_frac,
                  "  T: ", t_sign, t_whole, ".", t_frac, sep="")

        delay_ms(2000)
