"""
Compiling a small firmware for real, so a test can look at what came out.

Shared by the two suites that assert on generated code rather than on Python:
`test_timing.py`, which steps the result one cycle at a time, and
`test_uart.py`, which reads what it writes to the serial port. Neither can
learn anything from importing the driver -- the numbers they check only exist
after the compiler has had its say.

A probe that does not *compile* is a failure, not a skip: a library that no
longer builds must not pass its own suite quietly. Missing tooling is the one
thing that skips, which keeps `pytest` useful on a machine without a compiler.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PORT_B, PORT_D = 0, 2

PROJECT = """\
[project]
name = "dht-probe"
version = "0.1.0"
dependencies = []

[tool.pymcu]
target = "atmega328p"
frequency = 16000000
sources = "src"
entry = "main.py"
"""

# Twelve lines that say whether this compiler binds a function's parameters at
# all. Up to 0.1.0a9 a module-level global won over a parameter of the same
# name, and `doubled(3)` returned 200 -- which no library can be written
# against, since it means a firmware picks what its arguments are by choosing
# names. Fixed in 0.1.0a10, in two halves: @inline expansions first, plain defs
# after. Nothing in this library is asserted on a compiler that fails it.
PARAMETER_BINDING_PROBE = """\
from pymcu.types import uint16

factor: uint16 = 100


def doubled(factor: uint16) -> uint16:
    return factor * 2


def main():
    print(doubled(3))
    print("done")
    while True:
        pass
"""


def pymcu_executable() -> str | None:
    """
    Prefer the pymcu that lives beside the interpreter running this test.

    A `pymcu` earlier on PATH (a globally pinned release, say) would build
    against a different library install than the editable one under test --
    silently exercising the wrong sources. The venv running pytest is the one
    `uv pip install -e` was pointed at, so its own bin/ is trusted first; a
    bare `shutil.which` is the fallback for a pymcu run outside a venv layout.
    """
    beside_interpreter = Path(sys.executable).parent / "pymcu"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("pymcu")


def build(tmp_path_factory, name: str, source: str) -> str:
    """Compile *source* as a one-file firmware and return its Intel HEX."""
    pymcu = pymcu_executable()
    if pymcu is None:
        pytest.skip("needs a pymcu compiler on PATH")

    project = tmp_path_factory.mktemp(name)
    (project / "src").mkdir()
    (project / "pyproject.toml").write_text(PROJECT)
    (project / "src" / "main.py").write_text(source)

    result = subprocess.run([pymcu, "build"], cwd=project, capture_output=True, text=True)
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip().splitlines()
        pytest.fail(f"the {name} probe did not build:\n" + "\n".join(output[-8:]))

    firmware = project / "dist" / "firmware.hex"
    if not firmware.exists():
        pytest.fail(f"no firmware.hex produced for {name}")
    return firmware.read_text()


def transcript(hex_text: str, until: str, max_ms: float = 5000) -> str:
    """Run *hex_text* until it has written *until*, and return what it said."""
    from avr8sharp import Simulation

    sim = Simulation.create().with_frequency(16_000_000).with_hex(hex_text)
    # PD2 is the DHT data line. An unregistered port answers `IN PINx` with
    # zero, which is a different failure from the open line a probe expects.
    sim.add_gpio(PORT_D)
    serial = sim.add_usart0()
    sim.run_until_serial(serial, until, max_ms=max_ms)
    return serial.text


def require_parameter_binding(tmp_path_factory) -> None:
    """
    Skip out loud on a compiler that cannot bind a parameter.

    A version check would be the obvious thing and is the wrong one here: a
    working tree's compiler reports whatever version was last released, so the
    binary that fixed this still called itself 0.1.0a9 for a while. The
    question is what the compiler *does*, and it takes one small build to ask.
    """
    global _parameter_binding
    if _parameter_binding is None:
        # Waited on "done" rather than on the answer: a compiler that gets this
        # wrong prints 200, and waiting for "6" would burn the whole simulated
        # timeout and raise instead of reporting what happened.
        text = transcript(
            build(tmp_path_factory, "binding", PARAMETER_BINDING_PROBE), "done")
        _parameter_binding = text.splitlines()[0].strip() == "6"
    if not _parameter_binding:
        pytest.skip(
            "this compiler lets a module-level global take over a parameter of "
            "the same name (fixed in pymcu-compiler 0.1.0a10); no argument this "
            "driver passes can be relied on to arrive"
        )


_parameter_binding: bool | None = None
