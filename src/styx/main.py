import argparse
import json
import pathlib

import tomli as tomllib  # Remove once we move to python 3.11

from styx.boutiques.utils import boutiques_from_dict
from styx.compiler.core import compile_definitions, compile_descriptor
from styx.compiler.settings import CompilerSettings, DefsMode


def load_settings_from_toml(file_path: str | pathlib.Path) -> dict[str, str] | None:
    try:
        with open(file_path, "rb") as f:
            settings = tomllib.load(f)
            return settings
    except FileNotFoundError:
        return None


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compile JSON descriptors to Python modules")
    parser.add_argument("input_folder", type=pathlib.Path, help="Path to the input folder containing JSON descriptors")
    parser.add_argument(
        "-o", "--output-folder", type=pathlib.Path, help="Path to the output folder for compiled Python modules"
    )
    parser.add_argument("-c", "--config", type=pathlib.Path, help="Path to the configuration file")
    args = parser.parse_args()

    input_folder: pathlib.Path = args.input_folder
    output_folder: pathlib.Path | None = args.output_folder
    config_file: pathlib.Path | None = args.config

    compiler_settings = None
    if config_file:
        compiler_settings = load_settings_from_toml(config_file)
    if compiler_settings is None:
        compiler_settings = load_settings_from_toml(input_folder / "styx.toml")
    if compiler_settings is None:
        compiler_settings = load_settings_from_toml(input_folder / "pyproject.toml")

    settings = CompilerSettings(
        defs_mode=DefsMode.IMPORT,
    )

    if settings.defs_mode == DefsMode.IMPORT:
        defs_path: str | pathlib.Path = "styxdefs.py"
        if output_folder is not None:
            # write out the definitions to a separate file
            defs_path = output_folder / defs_path
            defs = compile_definitions()
            with open(defs_path, "w") as defs_file:
                defs_file.write(defs)
        print(f"Compiled definitions to {defs_path}")

    json_files = input_folder.glob("**/*.json")

    for json_path in json_files:
        output_module_path = json_path.parent.relative_to(input_folder).parts
        output_file_name = f"{json_path.stem}.py"

        settings.defs_module_path = "." * len(output_module_path) + "styxdefs"

        with open(json_path, "r") as json_file:
            json_data = json.load(json_file)

        descriptor = boutiques_from_dict(json_data)
        code = compile_descriptor(descriptor, settings)

        if output_folder:
            output_path = output_folder / pathlib.Path(*output_module_path)
            output_path.mkdir(parents=True, exist_ok=True)
            output_path = output_path / output_file_name
            with open(output_path, "w") as py_file:
                py_file.write(code)
            print(f"Compiled {json_path} to {output_path}")
        else:
            print(f"Compiled {json_path} -> {pathlib.Path(*output_module_path) / output_file_name}: {'---' * 10}")
            print(code)
            print("---" * 10)


if __name__ == "__main__":
    main()
