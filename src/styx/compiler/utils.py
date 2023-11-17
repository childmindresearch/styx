"""Compiler utilities."""


def optional_float_to_int(value: float | None) -> int | None:
    """Convert an optional float to an optional int."""
    return int(value) if value is not None else None
