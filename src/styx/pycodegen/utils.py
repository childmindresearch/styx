import re
from typing import Union

from .string_case import (
    camel_case,
    pascal_case,
    screaming_snake_case,
    snake_case,
)


def ensure_python_symbol(name: str) -> str:
    """Ensure that a string is a valid Python symbol.

    Args:
        name (str): The string to be converted.

    Returns:
        str: A valid Python symbol.
    """
    # Remove invalid characters
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Prepend 'v_' if name starts with a digit
    name = re.sub(r"^[0-9]", "v_", name)

    return name


def python_camelize(string: str) -> str:
    """Converts a string to camel case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return camel_case(ensure_python_symbol(string))


def python_pascalize(string: str) -> str:
    """Converts a string to pascal case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return pascal_case(ensure_python_symbol(string))


def python_snakify(string: str) -> str:
    """Converts a string to snake case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return snake_case(ensure_python_symbol(string))


def python_screaming_snakify(string: str) -> str:
    """Converts a string to screaming snake case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return screaming_snake_case(ensure_python_symbol(string))


def enquote(
    s: str,
    quote: str = '"',
) -> str:  # noqa
    """Put a string in "quotes"."""
    return f"{quote}{s}{quote}"


def enbrace(
    s: str,
    brace_type: str = "{",
) -> str:  # noqa
    """Put a string in {braces}."""
    _right_brace = {"{": "}", "[": "]", "(": ")"}
    return f"{brace_type}{s}{_right_brace[brace_type]}"


_TYPE_PYPRIMITIVE = str | float | int | bool
_TYPE_PYLITERAL = Union[_TYPE_PYPRIMITIVE, list["_TYPE_PYLITERAL"]]


def as_py_literal(obj: _TYPE_PYLITERAL, quote: str = '"') -> str:
    """Convert an object to a Python literal expression."""
    if isinstance(obj, list):
        return enbrace(", ".join([as_py_literal(o, quote) for o in obj]), "[")
    if isinstance(obj, str):
        return enquote(obj, quote)
    else:
        return str(obj)


def linebreak_line(text: str, width: int = 80) -> list[str]:
    """Insert linebreaks into a line of text. Breaks lines at word boundaries."""
    words = text.split()
    lines = []
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            if line:
                line += " "
            line += word
    lines.append(line)
    return lines


def linebreak_paragraph(text: str, width: int = 80, first_line_width: int = 80) -> list[str]:
    """Insert linebreaks into a paragraph of text. Breaks lines at word boundaries."""
    lines = text.splitlines()
    wrapped_lines = []
    first = True
    for line in lines:
        if first:
            wrapped_lines.extend(linebreak_line(line, width=first_line_width))
            first = False
        else:
            wrapped_lines.extend(linebreak_line(line, width=width))
    return wrapped_lines
