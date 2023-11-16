import typing

P = typing.TypeVar("P", contravariant=True)
"""Input host file type."""
R = typing.TypeVar("R", covariant=True)
"""Output host file type."""


class Execution(typing.Protocol[P, R]):
    """Execution object used to execute commands.

    Created by `Runner.start_execution()`.
    """

    def input_file(self, host_file: P) -> str:
        """Resolve host input files.

        Returns a local filepath.
        Called (potentially multiple times) after
        `Runner.start_execution()` and before `Runner.run()`.
        """
        ...

    def run(self, cargs: list[str]) -> None:
        """Run the command.

        Called after all `Execution.input_file()`
        calls and before `Execution.output_file()` calls.
        """
        ...

    def output_file(self, local_file: str) -> R:
        """Resolve local output files.

        Returns a host filepath.
        Called (potentially multiple times) after
        `Runner.run()` and before `Execution.finalize()`.
        """
        ...

    def finalize(self) -> None:
        """Finalize the execution.

        Called after all `Execution.output_file()` calls.
        """
        ...


class Runner(typing.Protocol[P, R]):
    """Runner object used to execute commands.

    Possible examples would be `LocalRunner`,
    `DockerRunner`, `DebugRunner`, ...
    Used as a factory for `Execution` objects.
    """

    def start_execution(self, tool_name: str) -> Execution[P, R]:
        """Start an execution.

        Called before any `Execution.input_file()` calls.
        """
        ...
