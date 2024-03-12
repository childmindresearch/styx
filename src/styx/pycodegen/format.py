"""Format code using ruff."""

import subprocess
from pathlib import Path


def format_code(code: str) -> str | None:
    """Format code using ruff."""
    try:
        formatted = subprocess.check_output(
            [
                "ruff",
                "format",
                "--config",
                Path(__file__).parent / "dynruff.toml",
                "-",
            ],
            input=code,
            encoding="utf-8",
        )
        return formatted
    except subprocess.CalledProcessError as _:
        return None
