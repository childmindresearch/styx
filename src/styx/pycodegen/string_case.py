import re

_RX_ENSURE_CAMEL = re.compile(r"(?<=[A-Z])(?!$)(?!_)(?![A-Z])")
_RX_AFTER_UNDERSCORE = re.compile(r"(?:^|(?<=_))([a-z])")


def snake_case(string: str) -> str:
    """Converts a string to snake case.

    Consecutive uppercase letters do not receive underscores between them.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return _RX_ENSURE_CAMEL.sub("_", string[::-1]).lower()[::-1]


def pascal_case(string: str) -> str:
    """Converts a string to pascal case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return _RX_AFTER_UNDERSCORE.sub(lambda m: m.group(1).upper(), snake_case(string)).replace("_", "")


def camel_case(string: str) -> str:
    """Converts a string to camel case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    s = pascal_case(string)
    return s[0].lower() + s[1:]


def screaming_snake_case(string: str) -> str:
    """Converts a string to screaming snake case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return snake_case(string).upper()
