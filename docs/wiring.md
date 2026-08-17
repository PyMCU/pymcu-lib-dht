# Wiring

DHT11, DHT22/AM2302 and DHT21/AM2301 all use the same three or four pins, in the same
order — this page applies to the whole family.

## Arduino Uno / ATmega328P

```
      DHT11 / DHT22 / DHT21        Arduino Uno
   +---------+
   |   VCC   |------------------- 5V
   |         |
   |   OUT   |----+-------------- D2 (PD2)
   |         |    |
   |         |   [4.7k]  (only if not on the breakout board already)
   |         |    |
   |         |   5V
   |         |
   |   GND   |------------------- GND
   +---------+
```

- `DATA` can be any of `PD2`-`PD7` — pass the pin name string to `DHT11(...)`,
  `DHT22(...)` or `DHT21(...)`. `PD0`/`PD1` are reserved for UART (`RX`/`TX`) and are
  not accepted by `_dht_avr.py`.
- A three-pin breakout board (labelled `VCC`, `OUT`/`DATA`/`SIG`, `GND`) already has
  the pull-up resistor on the board. A bare four-pin sensor (`VDD`, `DATA`, `NC`,
  `GND`) needs the external 4.7 kOhm resistor shown above.
- 5V supply is what every model in the family is specified for; they also run at 3.3V
  with reduced range, if that's what your board provides.

## Pin choice and the driver's dispatch

`_dht_avr.py` resolves the pin name to a register/bit pair with a chain of
`if pin_name == "PDn":` comparisons — the same pattern the stdlib GPIO HAL uses for
`pin_set_mode`/`pin_high`. The compiler constant-folds this at compile time: only the
branch matching the pin you actually passed survives in the compiled firmware, so
`DHT11("PD2")`/`DHT22("PD2")` costs nothing for the five pins you didn't choose.
