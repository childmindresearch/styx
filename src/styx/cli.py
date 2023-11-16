"""Command line interface for styx."""

import argparse
import json
import pathlib as pl

from styx.boutiques import model
from styx.compiler.core import compile_descriptor
from styx.compiler.settings import CompilerSettings


def _cli() -> None:
    """Command line interface for styx."""
    parser = argparse.ArgumentParser(
        prog="styx",
        description="Styx is a command line tool Python wrapper code generator.",
    )

    parser.add_argument(
        "input",
        type=pl.Path,
        help="Path to the input JSON Boutiques descriptor.",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=pl.Path,
        help="Path to the output Python file.",
    )

    args = parser.parse_args()

    path_descriptor: pl.Path = args.input
    path_output: pl.Path | None = args.output

    settings = CompilerSettings()

    with open(path_descriptor, "r") as json_file:
        json_data = json.load(json_file)

    data = model.Tool(**json_data)  # type: ignore

    compiled_module = compile_descriptor(data, settings)

    if path_output is None:
        print(compiled_module)
    else:
        with open(path_output, "w") as py_file:
            py_file.write(compiled_module)


if __name__ == "__main__":
    _cli()
