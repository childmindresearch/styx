import shlex

import styx.boutiques.model


def boutiques_from_dict(data: dict) -> styx.boutiques.model.Tool:  # type: ignore
    """Create a Boutiques model from a dictionary.

    Args:
        data (dict): The dictionary.

    Returns:
        styx.boutiques.model.Tool: The Boutiques model.
    """
    return styx.boutiques.model.Tool(**data)  # type: ignore


def boutiques_split_command(command: str) -> list[str]:
    """Split a Boutiques command into a list of arguments.

    Args:
        command (str): The Boutiques command.

    Returns:
        list[str]: The list of arguments.
    """
    # shlex waits for stdin if None is passed, make sure this doesn't happen
    assert command is not None, "Command cannot be None"
    args = shlex.split(command)

    return args


# Helper types
InputType = styx.boutiques.model.BoutiquesInput  # type: ignore
OutputType = (
    styx.boutiques.model.OutputFiles  # type: ignore
    | styx.boutiques.model.OutputFiles1  # type: ignore
    | styx.boutiques.model.OutputFiles2  # type: ignore
    | styx.boutiques.model.OutputFiles3  # type: ignore
)
