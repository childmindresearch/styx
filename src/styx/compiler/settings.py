"""Compiler settings."""

import pathlib
from dataclasses import dataclass
from enum import Enum


class DefsMode(Enum):
    """Runtime definitions mode."""

    INLINE = 0
    IMPORT = 1
    DEFS_ONLY = 2


@dataclass
class CompilerSettings:
    """Compiler settings."""

    input_path: pathlib.Path
    output_path: pathlib.Path | None = None

    defs_module_path: str | None = None
    defs_mode: DefsMode = DefsMode.IMPORT