import json

from styx.boutiques import model
from styx.compiler.core import compile_descriptor
from styx.compiler.settings import CompilerSettings


def main() -> None:
    with open("examples/bet.json", "r") as json_file:
        json_data = json.load(json_file)
    data = model.Tool(**json_data)  # type: ignore

    settings = CompilerSettings()

    print(compile_descriptor(data, settings))


if __name__ == "__main__":
    main()
