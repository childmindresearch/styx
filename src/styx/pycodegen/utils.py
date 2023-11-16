import keyword
import re

_RX_ENSURE_CAMEL = re.compile(r"(?<=[A-Z])(?!$)(?!_)(?![A-Z])")


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
    # Avoid python keyword collisions
    while keyword.iskeyword(name):
        name = f"{name}_"

    return name


def ensure_snake_case(string: str) -> str:
    """Converts a string to snake case.

    Consecutive uppercase letters do not receive underscores between them.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return _RX_ENSURE_CAMEL.sub("_", string[::-1]).lower()[::-1]


def ensure_camel_case(string: str) -> str:
    """Converts a string to camel case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return _RX_ENSURE_CAMEL.sub("_", string).title().replace("_", "")


def enquote(s: str) -> str:  # noqa
    """Put a string in "quotes"."""
    return f'"{s}"'


def as_py_literal(obj: str | float | int | bool) -> str:
    """Convert an object to a Python literal expression."""
    if isinstance(obj, str):
        return enquote(obj)
    else:
        return str(obj)
