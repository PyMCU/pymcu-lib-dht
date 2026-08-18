"""
Enough of PyMCU to import the library under plain CPython.

The modules here target a microcontroller: `pymcu.types` annotations, the
`__CHIP__` constant and the bit-banging in `_dht/avr.py` all mean something
only to the compiler. Stubbing them lets the framing logic -- decode math and
the three API shapes, the part most likely to have an off-by-one -- be tested
on a laptop.

Only what talks to a pin is faked, which comes to a single method. Both
`_dht/decode.py` and `_dht/core.py` are the real files: the first is plain
arithmetic with no chip dependency, and the second is the sentinel, the two
start-signal durations and a `Frame` whose `read()` is swapped for one that
returns a scripted 40-bit frame (or FRAME_ERROR) per test. The architecture
dispatch that method normally performs is what hides the chip imports, so
never calling the real one is enough to keep this runnable on a laptop.

What the compiler does with these files is verified separately, by compiling
the examples for real.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

# The sources the compiler reads, which is the only part of the package
# that is Python meant to be read at all.
SOURCE_DIR = Path(__file__).resolve().parents[1] / "src" / "pymcu_lib_dht" / "mcu"
sys.path.insert(0, str(SOURCE_DIR))


def _install_stubs() -> None:
    pymcu = ModuleType("pymcu")
    pymcu.__path__ = []
    sys.modules["pymcu"] = pymcu

    types_mod = ModuleType("pymcu.types")

    def _identity(f):
        return f

    class _Int:
        """Stands in for uintN/intN: annotations only, never constructed."""

        def __class_getitem__(cls, item):
            return cls

    types_mod.inline = _identity
    types_mod.uint8 = _Int
    types_mod.uint16 = _Int
    types_mod.int16 = _Int
    types_mod.uint32 = _Int
    sys.modules["pymcu.types"] = types_mod
    pymcu.types = types_mod

    chips = ModuleType("pymcu.chips")

    class _Chip(str):
        arch = "avr"
        name = "atmega328p"

    chips.__CHIP__ = _Chip("atmega328p")
    sys.modules["pymcu.chips"] = chips
    pymcu.chips = chips

    exceptions = ModuleType("pymcu.exceptions")

    class CompileError(Exception):
        pass

    exceptions.CompileError = CompileError
    sys.modules["pymcu.exceptions"] = exceptions
    pymcu.exceptions = exceptions

    # The real decoder: plain arithmetic, no hardware, worth testing for real.
    # _dht is a package on the device too, so it is one here: the stub core
    # and the real decoder have to hang off the same parent module or the
    # library's own `from _dht.core import ...` would not resolve.
    private = ModuleType("_dht")
    private.__path__ = [str(SOURCE_DIR / "_dht")]
    sys.modules["_dht"] = private

    spec = importlib.util.spec_from_file_location(
        "_dht.decode", SOURCE_DIR / "_dht" / "decode.py")
    decode = importlib.util.module_from_spec(spec)
    sys.modules["_dht.decode"] = decode
    spec.loader.exec_module(decode)
    private.decode = decode

    # The core is loaded for real as well, and then has exactly one method
    # replaced. It owns the sentinel and the two start-signal durations, and a
    # stub that restated them would agree with itself no matter what the driver
    # says -- the whole point of the start-signal test is that 18 ms and 1 ms
    # cannot collapse into one value. Only `read()` talks to a pin, and only
    # `read()` is scripted; the architecture dispatch inside it is never
    # reached, so the chip imports it hides behind never run.
    spec = importlib.util.spec_from_file_location(
        "_dht.core", SOURCE_DIR / "_dht" / "core.py")
    core = importlib.util.module_from_spec(spec)
    sys.modules["_dht.core"] = core
    spec.loader.exec_module(core)
    private.core = core

    def read(self, start_low_ms):
        self.last_start_low_ms = start_low_ms
        return core.Frame.next_frame

    core.Frame.read = read
    core.Frame.next_frame = 0x28000000   # 40.0% RH, 0.0 C -- set per test
    core.Frame.FRAME_ERROR_VALUE = core.FRAME_ERROR


_install_stubs()
