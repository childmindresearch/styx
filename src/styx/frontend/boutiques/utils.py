"""This module contains the `boutiques_split_command` function."""

import shlex


def boutiques_split_command(command: str) -> list[str]:
    """Split a Boutiques command into a list of arguments.

    Args:
        command (str): The Boutiques command.

    Returns:
        list[str]: The list of arguments.
    """
    # shlex waits for stdin if None is passed (endless loop), ensure this never happens
    if command is None:
        raise ValueError("Command cannot be None")
    return shlex.split(command)
