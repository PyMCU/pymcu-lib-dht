"""
Two sensor models, three APIs, one wire.

The frames below are the datasheet's own worked examples, so a failure here
means the decode disagrees with the datasheet rather than with a number
someone made up:

  DHT11 0x23 0x00 0x18 0x00   ->  35% RH, 24 C          (integer counts)
  DHT22 0x02 0x92 0x01 0x0D   ->  65.8% RH, 26.9 C      (tenths, 16-bit)
  DHT22 0x02 0x92 0x80 0x45   ->  65.8% RH, -6.9 C      (sign in bit 15)

The negative case is the one worth spelling out: the DHT22 does not use two's
complement. Bit 15 is a sign flag and the low 15 bits are the magnitude, so a
decoder that sign-extends instead of masking reads -6.9 C as 3277.3 C and
still looks plausible in every positive test.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SOURCE_DIR = Path(__file__).resolve().parents[1] / "src" / "pymcu_lib_dht" / "mcu"

DHT11_FRAME = 0x23001800
DHT22_FRAME = 0x0292010D
DHT22_BELOW_ZERO = 0x02928045

# What the sensor sends when the host holds the line low to start an exchange.
# The two models disagree, and getting it backwards is a silent failure: an
# 18 ms start on a DHT22 is out of spec but often still answers on the bench,
# so only asserting on it keeps the two apart.
START_LOW_DHT11_MS = 18
START_LOW_DHT22_MS = 1


def _load(relative_path: str, name: str):
    """Import a layer module by file: two of them are both called `dht`."""
    spec = importlib.util.spec_from_file_location(name, SOURCE_DIR / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def native():
    return _load("dht.py", "native_dht")


@pytest.fixture
def micropython():
    return _load("compat/micropython/dht.py", "mp_dht")


@pytest.fixture
def circuitpython():
    return _load("adafruit_dht.py", "cp_dht")


@pytest.fixture
def decode():
    import _dht.decode as _dht_decode
    return _dht_decode


@pytest.fixture(autouse=True)
def frame():
    """Every test starts from a scripted DHT11 reading it can override."""
    from _dht.core import Frame
    Frame.next_frame = DHT11_FRAME
    yield Frame
    Frame.next_frame = DHT11_FRAME


class _Pin:
    """What machine.Pin looks like from outside: a name the HAL understands."""

    def __init__(self, name, *_args, **_kwargs):
        self._name = name


class TestDecoding:
    """Plain arithmetic on bytes the core already fetched -- the real module."""

    def test_dht11_integer_counts_become_tenths(self, decode):
        humidity, temperature = decode.decode_dht11(DHT11_FRAME)
        assert (humidity, temperature) == (350, 240)

    def test_dht22_reports_tenths_across_two_bytes(self, decode):
        humidity, temperature = decode.decode_dht22(DHT22_FRAME)
        assert (humidity, temperature) == (658, 269)

    def test_dht22_below_zero_is_a_sign_bit_not_twos_complement(self, decode):
        humidity, temperature = decode.decode_dht22(DHT22_BELOW_ZERO)
        assert humidity == 658
        assert temperature == -69

    def test_the_two_models_do_not_share_a_decoder(self, decode):
        """A DHT22 frame read as a DHT11 is wrong, and that is the point."""
        assert decode.decode_dht11(DHT22_FRAME) != decode.decode_dht22(DHT22_FRAME)


class TestNative:
    def test_dht11_measures_and_reports_tenths(self, native):
        sensor = native.DHT11("PD2")
        sensor.measure()
        assert sensor.failed == 0
        assert sensor.humidity() == 350
        assert sensor.temperature() == 240

    def test_dht22_measures_and_reports_tenths(self, native, frame):
        frame.next_frame = DHT22_FRAME
        sensor = native.DHT22("PD2")
        sensor.measure()
        assert sensor.failed == 0
        assert sensor.humidity() == 658
        assert sensor.temperature() == 269

    def test_each_model_holds_the_line_low_for_its_own_time(self, native, frame):
        eleven = native.DHT11("PD2")
        eleven.measure()
        assert eleven._frame.last_start_low_ms == START_LOW_DHT11_MS

        frame.next_frame = DHT22_FRAME
        twentytwo = native.DHT22("PD2")
        twentytwo.measure()
        assert twentytwo._frame.last_start_low_ms == START_LOW_DHT22_MS

    def test_a_failed_read_is_flagged_and_keeps_the_last_value(self, native, frame):
        sensor = native.DHT11("PD2")
        sensor.measure()
        assert sensor.humidity() == 350

        frame.next_frame = frame.FRAME_ERROR_VALUE
        sensor.measure()
        assert sensor.failed == 1
        assert sensor.humidity() == 350

    def test_dht21_is_the_dht22(self, native):
        # AM2301/DHT21 is the same protocol and byte layout. An alias, so the
        # two can never drift apart; asserted so a later edit cannot quietly
        # turn it into a second copy.
        assert native.DHT21 is native.DHT22


class TestMicroPython:
    """A MicroPython script must run unchanged."""

    def test_takes_a_machine_pin(self, micropython):
        sensor = micropython.DHT11(_Pin("PD2"))
        assert sensor._frame.pin == "PD2"

    def test_measure_then_read(self, micropython):
        sensor = micropython.DHT11(_Pin("PD2"))
        sensor.measure()
        assert sensor.humidity() == 350
        assert sensor.temperature() == 240

    def test_dht22_too(self, micropython, frame):
        frame.next_frame = DHT22_FRAME
        sensor = micropython.DHT22(_Pin("PD2"))
        sensor.measure()
        assert sensor.temperature() == 269

    def test_failure_is_a_flag_because_there_is_no_oserror(self, micropython, frame):
        sensor = micropython.DHT11(_Pin("PD2"))
        sensor.measure()
        frame.next_frame = frame.FRAME_ERROR_VALUE
        sensor.measure()
        assert sensor.failed == 1
        assert sensor.humidity() == 350


class TestCircuitPython:
    """A CircuitPython script must run unchanged -- including the floats."""

    def test_properties_report_degrees_not_tenths(self, circuitpython):
        sensor = circuitpython.DHT11("D2")
        assert sensor.humidity == 35.0
        assert sensor.temperature == 24.0

    def test_dht22_keeps_its_decimal_digit(self, circuitpython, frame):
        frame.next_frame = DHT22_FRAME
        sensor = circuitpython.DHT22("D2")
        assert sensor.temperature == pytest.approx(26.9)
        assert sensor.humidity == pytest.approx(65.8)

    def test_a_failed_read_raises(self, circuitpython, frame):
        frame.next_frame = frame.FRAME_ERROR_VALUE
        sensor = circuitpython.DHT11("D2")
        with pytest.raises(ValueError):
            _ = sensor.temperature

    def test_exit_is_harmless(self, circuitpython):
        circuitpython.DHT11("D2").exit()


def test_every_layer_reads_the_same_sensor(native, micropython, circuitpython, frame):
    """One sensor, three APIs: the wire does not care which one you wrote."""
    frame.next_frame = DHT22_FRAME

    a = native.DHT22("PD2")
    b = micropython.DHT22(_Pin("PD2"))
    c = circuitpython.DHT22("D2")

    a.measure()
    b.measure()

    assert a.temperature() == b.temperature() == 269
    assert c.temperature == pytest.approx(a.temperature() / 10)
