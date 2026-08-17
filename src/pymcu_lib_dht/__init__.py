"""
DHT11, DHT22/AM2302 and DHT21/AM2301 sensors for PyMCU.

Nothing here runs under CPython. The modules the compiler reads are package
data under mcu/, and PyMCU puts that directory -- and only that directory --
on the include path when a project depends on this distribution. From a
firmware they are top-level imports:

    from dht import DHT11, DHT22        # native and MicroPython
    from adafruit_dht import DHT22      # CircuitPython
"""
