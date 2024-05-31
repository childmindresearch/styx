"""Compiler settings."""

import pathlib
from dataclasses import dataclass


@dataclass
class CompilerSettings:
    """Compiler settings."""

    input_path: pathlib.Path | None = None
    output_path: pathlib.Path | None = None

    debug_mode: bool = False
