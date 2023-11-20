"""Static type declarations used by compiled code."""

from styx.pycodegen.core import indent

STYX_DEFINITIONS = [
    'P = typing.TypeVar("P")',
    '"""Input host file type."""',
    'R = typing.TypeVar("R")',
    '"""Output host file type."""',
    "",
    "",
    "class Execution(typing.Protocol[P, R]):",
    *indent(
        [
            '"""',
            "Execution object used to execute commands.",
            "Created by `Runner.start_execution()`.",
            '"""',
            "def input_file(self, host_file: P) -> str:",
            *indent(
                [
                    '"""',
                    "Resolve host input files.",
                    "Returns a local filepath.",
                    "Called (potentially multiple times) after "
                    "`Runner.start_execution()` and before `Runner.run()`.",
                    '"""',
                    "...",
                ]
            ),
            "def run(self, cargs: list[str]) -> None:",
            *indent(
                [
                    '"""',
                    "Run the command.",
                    "Called after all `Execution.input_file()` calls and " "before `Execution.output_file()` calls.",
                    '"""',
                    "...",
                ]
            ),
            "def output_file(self, local_file: str) -> R:",
            *indent(
                [
                    '"""',
                    "Resolve local output files.",
                    "Returns a host filepath.",
                    "Called (potentially multiple times) after " "`Runner.run()` and before `Execution.finalize()`.",
                    '"""',
                    "...",
                ]
            ),
            "def finalize(self) -> None:",
            *indent(
                [
                    '"""',
                    "Finalize the execution.",
                    "Called after all `Execution.output_file()` calls.",
                    '"""',
                    "...",
                ]
            ),
        ]
    ),
    "",
    "",
    "class Runner(typing.Protocol[P, R]):",
    *indent(
        [
            '"""',
            "Runner object used to execute commands.",
            "Possible examples would be `LocalRunner`, " "`DockerRunner`, `DebugRunner`, ...",
            "Used as a factory for `Execution` objects.",
            '"""',
            "def start_execution(self, tool_name: str) -> Execution[P, R]:",
            *indent(
                [
                    '"""',
                    "Start an execution.",
                    "Called before any `Execution.input_file()` calls.",
                    '"""',
                    "...",
                ]
            ),
        ]
    ),
]
