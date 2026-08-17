"""
The parts of this driver that a datasheet, not a unit test, has to agree with.

The DHT family has no clock line. A bit is a zero or a one purely by how long
the sensor holds the line high -- ~26-28 us against ~70 us -- and this driver
tells them apart by counting loop iterations, not by timing them. That makes
the threshold in `_dht_avr.py` a number about generated code: change the loop
body, or the optimiser, and 64 can drift to one side of a real bit without a
single test noticing. A sensor then reads 0% RH for ever, and the flash figure
still looks perfectly healthy. The NeoPixel driver in this project shipped
exactly that class of bug for months.

So the numbers are measured rather than argued about: each probe below is
compiled for real and stepped one cycle at a time on the emulator.

Three things are checked, each of which fails silently on hardware:

  * the counting loop, converted into what a real sensor would produce, has
    to land clear of the threshold on both sides;
  * the wait for an edge has to outlast the 80 us the sensor can spend on one
    level, or no reading ever completes;
  * the start pulse has to match the model being addressed -- 18 ms for the
    DHT11, ~1 ms for the DHT22, and the two must not collapse into one value.

Skipped when avr8sharp or a compiler is missing, which keeps `pytest` useful
on a machine with neither. A probe that does not *compile* is a failure, not
a skip: a library that no longer builds must not pass its own suite quietly.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CYCLE_NS = 62.5                 # 16 MHz

# Datasheet pulse widths, in microseconds.
ZERO_BIT_HIGH_US = (26, 28)
ONE_BIT_HIGH_US = (70, 75)
LONGEST_LEVEL_US = 80           # the ACK, and the low before every bit

START_LOW_DHT11_MS = 18
START_LOW_DHT22_MS = 1


def _driver_constant(name: str) -> int:
    """
    Read a constant out of the driver source.

    Not a copy of the number, and not an import either: a copy makes this file
    agree with itself no matter what the driver says -- the first draft had
    `HIGH_COUNT_THRESHOLD = 64` written here, and every test still passed with
    the driver set to 40, which is a value a real 0 bit reaches. Importing is
    no good either, since the module needs chip registers that only exist
    under the compiler.
    """
    source = (
        Path(__file__).resolve().parents[1]
        / "src" / "pymcu_lib_dht" / "_dht_avr.py"
    ).read_text()
    match = re.search(rf"^{name}: *\w+ *= *(\d+)", source, re.MULTILINE)
    assert match, f"{name} is not defined in _dht_avr.py"
    return int(match.group(1))


HIGH_COUNT_THRESHOLD = _driver_constant("HIGH_COUNT_THRESHOLD")

PROJECT = """\
[project]
name = "dht-timing-probe"
version = "0.1.0"
dependencies = []

[tool.pymcu]
target = "atmega328p"
frequency = 16000000
sources = "src"
entry = "main.py"
"""

# PD2 is driven high by the MCU itself, so PIND reads 1 and the counting loop
# runs its full 255 iterations. PB5 brackets the region being measured.
COUNT_PROBE = """\
from pymcu.types import uint8, asm
from pymcu.chips.atmega328p import DDRB, PORTB, DDRD, PORTD
from _dht_avr import _pd_high_count


def main():
    DDRB.value = DDRB.value | 0x20
    DDRD.value = DDRD.value | 0x04
    PORTD.value = PORTD.value | 0x04
    asm("NOP")
    asm("NOP")
    asm("CLI")
    PORTB.value = PORTB.value | 0x20
    result: uint8 = _pd_high_count(4)
    PORTB.value = PORTB.value & ~0x20
    asm("SEI")
    if result > 200:
        PORTB.value = PORTB.value | 0x10
    while True:
        pass
"""

# PD2 left as an input with no pull-up reads low, so waiting for a high can
# only end by running the timeout out -- which is the window being measured.
TIMEOUT_PROBE = """\
from pymcu.types import uint8, asm
from pymcu.chips.atmega328p import DDRB, PORTB
from _dht_avr import _pd_wait


def main():
    DDRB.value = DDRB.value | 0x20
    asm("CLI")
    PORTB.value = PORTB.value | 0x20
    result: uint8 = _pd_wait(4, 1)
    PORTB.value = PORTB.value & ~0x20
    asm("SEI")
    if result > 200:
        PORTB.value = PORTB.value | 0x10
    while True:
        pass
"""

# No marker pin here: the measured signal is PD2 itself, which dht_read drives
# low for the start of an exchange before releasing it. The read then fails on
# the missing sensor, which is fine -- the start pulse is already over.
START_PROBE = """\
from pymcu.types import uint32, asm
from _dht_avr import dht_read


def main():
    asm("CLI")
    frame: uint32 = dht_read("PD2", {start_low_ms})
    asm("SEI")
    while True:
        pass
"""

PORT_B, PORT_D = 0, 2


def _pymcu() -> str | None:
    """
    Prefer the pymcu that lives beside the interpreter running this test.

    A `pymcu` earlier on PATH (a globally pinned release, say) would build
    against a different library install than the editable one under test --
    silently exercising the wrong `_dht_avr.py`. The venv running pytest is
    the one `uv pip install -e` was pointed at, so its own bin/ is trusted
    first; a bare `shutil.which` is the fallback for a pymcu run outside a
    venv layout.
    """
    beside_interpreter = Path(sys.executable).parent / "pymcu"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("pymcu")


def _build(tmp_path_factory, name: str, source: str):
    pymcu = _pymcu()
    if pymcu is None:
        pytest.skip("needs a pymcu compiler on PATH")

    project = tmp_path_factory.mktemp(name)
    (project / "src").mkdir()
    (project / "pyproject.toml").write_text(PROJECT)
    (project / "src" / "main.py").write_text(source)

    build = subprocess.run([pymcu, "build"], cwd=project, capture_output=True, text=True)
    if build.returncode != 0:
        output = (build.stdout + build.stderr).strip().splitlines()
        pytest.fail(f"the {name} probe did not build:\n" + "\n".join(output[-8:]))

    firmware = project / "dist" / "firmware.hex"
    if not firmware.exists():
        pytest.fail(f"no firmware.hex produced for {name}")
    return firmware.read_text()


def _simulate(hex_text: str):
    from avr8sharp import Simulation

    sim = Simulation.create().with_frequency(16_000_000).with_hex(hex_text)
    # Both ports are registered even when only one is read: an unregistered
    # port answers `IN PINx` with zero, which silently turns the counting loop
    # into a loop that exits immediately.
    ports = {PORT_B: sim.add_gpio(PORT_B), PORT_D: sim.add_gpio(PORT_D)}
    return sim, ports


def _first_pulse(hex_text: str, port_index: int, bit: int, high: bool = True) -> int | None:
    """Length in cycles of the first high (or low) run on a pin."""
    sim, ports = _simulate(hex_text)
    port = ports[port_index]

    started = None
    previous = None
    for _ in range(2_000_000):
        sim.run_cycles(1)
        now = port.pin_high(bit) if high else not port.pin_high(bit)
        if previous is None:
            previous = now
            continue
        if now and not previous:
            started = sim.cpu.cycles
        elif previous and not now and started is not None:
            return sim.cpu.cycles - started
        previous = now
    return None


def _driven_low_cycles(hex_text: str, bit: int) -> int | None:
    """
    How long the MCU holds PD<bit> low as an output.

    Delimited by DDRD rather than by the pin level: an idle DHT line sits low
    in the emulator (an input with no pull-up), so there is no falling edge to
    find -- the pulse begins when the driver takes the pin over.
    """
    DDRD, PORTD = 0x2A, 0x2B
    mask = 1 << bit

    sim, _ports = _simulate(hex_text)
    started = None
    for _ in range(2_000_000):
        sim.run_cycles(1)
        driving_low = (sim.cpu.read(DDRD) & mask) and not (sim.cpu.read(PORTD) & mask)
        if driving_low and started is None:
            started = sim.cpu.cycles
        elif started is not None and not driving_low:
            return sim.cpu.cycles - started
    return None


def _counts_for(cycles_per_iteration: float, microseconds: float) -> float:
    return microseconds * 1000 / (cycles_per_iteration * CYCLE_NS)


@pytest.fixture(scope="module")
def emulator():
    pytest.importorskip("avr8sharp", reason="needs the emulator")


@pytest.fixture(scope="module")
def cycles_per_iteration(tmp_path_factory, emulator):
    hex_text = _build(tmp_path_factory, "count", COUNT_PROBE)
    cycles = _first_pulse(hex_text, PORT_B, 5)
    assert cycles is not None, "the counting loop never returned"
    return cycles / 255


class TestBitDiscrimination:
    """What a real sensor's pulses come to, in the units the driver compares."""

    def test_a_zero_bit_counts_well_below_the_threshold(self, cycles_per_iteration):
        longest_zero = _counts_for(cycles_per_iteration, ZERO_BIT_HIGH_US[1])
        assert longest_zero < HIGH_COUNT_THRESHOLD * 0.8, (
            f"a 0 bit counts to {longest_zero:.0f}, too close to the "
            f"threshold of {HIGH_COUNT_THRESHOLD} to survive a slow sensor"
        )

    def test_a_one_bit_counts_well_above_the_threshold(self, cycles_per_iteration):
        shortest_one = _counts_for(cycles_per_iteration, ONE_BIT_HIGH_US[0])
        assert shortest_one > HIGH_COUNT_THRESHOLD * 1.3, (
            f"a 1 bit counts to {shortest_one:.0f}, too close to the "
            f"threshold of {HIGH_COUNT_THRESHOLD}"
        )

    def test_the_longest_one_bit_does_not_saturate_the_counter(self, cycles_per_iteration):
        """The count is a uint8 that stops at 255; a saturated bit is unread."""
        longest_one = _counts_for(cycles_per_iteration, ONE_BIT_HIGH_US[1])
        assert longest_one < 255


class TestEdgeWaiting:
    def test_the_wait_outlasts_the_longest_level_the_sensor_holds(
        self, tmp_path_factory, emulator
    ):
        hex_text = _build(tmp_path_factory, "timeout", TIMEOUT_PROBE)
        cycles = _first_pulse(hex_text, PORT_B, 5)
        assert cycles is not None, "the wait never returned"
        window_us = cycles * CYCLE_NS / 1000
        assert window_us > LONGEST_LEVEL_US * 1.5, (
            f"the wait gives up after {window_us:.0f} us, but the sensor can "
            f"hold one level for {LONGEST_LEVEL_US} us -- no reading would "
            "ever complete"
        )


class TestStartPulse:
    """The one thing that differs between the models on the wire."""

    @pytest.mark.parametrize(("requested_ms", "name"), [
        (START_LOW_DHT11_MS, "DHT11"),
        (START_LOW_DHT22_MS, "DHT22"),
    ])
    def test_the_line_is_held_low_for_the_requested_time(
        self, tmp_path_factory, emulator, requested_ms, name
    ):
        hex_text = _build(
            tmp_path_factory,
            f"start_{requested_ms}",
            START_PROBE.format(start_low_ms=requested_ms),
        )
        cycles = _driven_low_cycles(hex_text, 2)
        assert cycles is not None, f"{name}: the line was never driven low"
        measured_ms = cycles * CYCLE_NS / 1_000_000
        assert measured_ms == pytest.approx(requested_ms, rel=0.1), (
            f"{name}: start pulse measured {measured_ms:.2f} ms, "
            f"asked for {requested_ms} ms"
        )
