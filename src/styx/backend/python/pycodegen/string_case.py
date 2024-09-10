import re

_RX_ENSURE_CAMEL = re.compile(r"(?<=[A-Z])(?!$)(?!_)(?![A-Z])")
_RX_LOW_AFTER_START_OR_UNDERSCORE = re.compile(r"(?:^|(?<=_))([a-z])")
_RX_UP_AFTER_START = re.compile(r"^([A-Z])")


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
    return _RX_LOW_AFTER_START_OR_UNDERSCORE.sub(lambda m: m.group(1).upper(), snake_case(string)).replace("_", "")


def camel_case(string: str) -> str:
    """Converts a string to camel case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return _RX_UP_AFTER_START.sub(lambda m: m.group(0).lower(), pascal_case(string))


def screaming_snake_case(string: str) -> str:
    """Converts a string to screaming snake case.

    Args:
        string: The string to convert.

    Returns:
        The converted string.
    """
    return snake_case(string).upper()
