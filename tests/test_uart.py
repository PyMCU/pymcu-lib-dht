"""
What the UART monitor actually says, byte for byte.

The example in `examples/uart-monitor/` documents its own output as
`H: 65.3  T: -5.5`, and for a while it did not produce it: the minus sign was
held in a plain `str` local, which PyMCU has no runtime representation for.
That compiled without a word and sent the number 45 -- the character code of
`-` -- down the wire, so the reading came out as `T: 455.5`. Nothing in the
suite looked at the output, so nothing failed.

These tests read the serial port. The first checks the shape a reading is
formatted into, on the values that break a naive formatter: a magnitude of
exactly 1000, a zero, and a tenth below zero, where the sign belongs to the
whole number and not to the digit after the point. The second compiles the
example as shipped and reads its first two lines -- with no sensor on PD2 the
read times out, which is exactly the path that has to say `read error` rather
than print a number at somebody.

Skipped when avr8sharp or a compiler is missing.
"""

from pathlib import Path

import pytest

from _probe import build, transcript

EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples" / "uart-monitor" / "src" / "main.py"
)

# The same three prints the example uses, fed from a table instead of a
# sensor. Reading a real DHT22 needs a real DHT22; the formatting does not.
FORMAT_PROBE = """\
from pymcu.types import int16, uint16

HUMIDITY: list[uint16] = [653, 1000, 0, 5]
TEMPERATURE: list[int16] = [-55, 269, 0, -1]


def main():
    i: uint16 = 0
    while i < 4:
        h: uint16 = HUMIDITY[i]
        print(f"H: {h // 10}.{h % 10}  T: ", end="")

        t: int16 = TEMPERATURE[i]
        if t < 0:
            t = -t
            print("-", end="")
        print(f"{t // 10}.{t % 10}")
        i = i + 1
    print("done")
    while True:
        pass
"""

EXPECTED = [
    "H: 65.3  T: -5.5",
    "H: 100.0  T: 26.9",
    "H: 0.0  T: 0.0",
    "H: 0.5  T: -0.1",
]


@pytest.fixture(scope="module")
def emulator():
    pytest.importorskip("avr8sharp", reason="needs the emulator")


def test_a_reading_is_formatted_as_tenths_with_its_sign(tmp_path_factory, emulator):
    text = transcript(build(tmp_path_factory, "format", FORMAT_PROBE), "done")
    assert text.splitlines()[:4] == EXPECTED


def test_the_example_says_what_it_documents_when_no_sensor_answers(
    tmp_path_factory, emulator
):
    hex_text = build(tmp_path_factory, "monitor", EXAMPLE.read_text())
    lines = transcript(hex_text, "read error").splitlines()
    assert lines[:2] == ["DHT22 ready", "read error"]
