"""
Enough of PyMCU to import the library under plain CPython.

The modules here target a microcontroller: `pymcu.types` annotations, the
`__CHIP__` constant and the bit-banging in `_dht_avr.py` all mean something
only to the compiler. Stubbing them lets the framing logic -- decode math and
the three API shapes, the part most likely to have an off-by-one -- be tested
on a laptop.

`_dht_decode.py` is *not* stubbed: it is plain arithmetic with no chip
dependency, so the real file is loaded and exercised for real. Only
`_dht_core.Frame` is faked, since only it talks to hardware -- its `read()`
returns a scripted 40-bit frame (or FRAME_ERROR) per test instead of bit-
banging a pin.

What the compiler does with these files is verified separately, by compiling
the examples for real.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "pymcu_lib_dht"
sys.path.insert(0, str(PACKAGE_DIR))


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
    spec = importlib.util.spec_from_file_location("_dht_decode", PACKAGE_DIR / "_dht_decode.py")
    decode = importlib.util.module_from_spec(spec)
    sys.modules["_dht_decode"] = decode
    spec.loader.exec_module(decode)

    # The core is the one module that talks to the hardware; under CPython it
    # returns a scripted frame, which is what the tests assert on.
    core = ModuleType("_dht_core")

    class Frame:
        next_frame = 0x28000000   # 40.0% RH, 0.0 C -- overridable per test
        FRAME_ERROR_VALUE = 0xFFFFFFFF

        def __init__(self, pin):
            self.pin = pin
            self.reads = 0

        def read(self, start_low_ms):
            self.reads += 1
            self.last_start_low_ms = start_low_ms
            return Frame.next_frame

    core.Frame = Frame
    core.FRAME_ERROR = Frame.FRAME_ERROR_VALUE
    sys.modules["_dht_core"] = core


_install_stubs()
