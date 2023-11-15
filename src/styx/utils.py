import keyword
import re


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
    return re.sub(r"(?<=[A-Z])(?!$)(?!_)(?![A-Z])", "_", string[::-1]).lower()[::-1]


def ensure_camel_case(string: str) -> str:
    """Converts a string to camel case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return (
        re.sub(r"(?<=[A-Z])(?!$)(?!_)(?![A-Z])", "_", string).title().replace("_", "")
    )


def enquote(s: str) -> str:
    """Enquote a string."""
    return f'"{s}"'
