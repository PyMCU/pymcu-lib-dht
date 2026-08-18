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
