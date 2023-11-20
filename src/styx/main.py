import json

from styx.boutiques.utils import boutiques_from_dict
from styx.compiler.core import compile_descriptor
from styx.compiler.settings import CompilerSettings, DefsMode


def main() -> None:
    settings = CompilerSettings(defs_mode=DefsMode.IMPORT)
    with open("examples/bet.json", "r") as json_file:
        json_data = json.load(json_file)
    descriptor = boutiques_from_dict(json_data)
    print(compile_descriptor(descriptor, settings))


if __name__ == "__main__":
    main()
