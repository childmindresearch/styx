"""Test command line argument building."""

import importlib.util
from types import ModuleType

import styx.boutiques.utils
import styx.compiler.core
import styx.compiler.settings
import styx.runners.core

_BT_TYPE_STRING = "String"
_BT_TYPE_NUMBER = "Number"
_BT_TYPE_FILE = "File"
_BT_TYPE_FLAG = "Flag"


def _dynamic_module(source_code: str, module_name: str) -> ModuleType:
    """Create a dynamic module."""
    module_spec = importlib.util.spec_from_loader(module_name, loader=None)
    assert module_spec is not None  # mypy
    module = importlib.util.module_from_spec(module_spec)
    exec(source_code, module.__dict__)
    # TODO: Does this module need to be unloaded somehow after use?
    return module


def _boutiques_dummy(descriptor: dict, dummy_output: bool = True) -> dict:
    """Add required meta data placeholders to a boutiques descriptor."""
    dummy = {
        "name": "dummy",
        "tool-version": "1.0",
        "description": "Dummy description",
        "command-line": "dummy",
        "schema-version": "0.5",
        "container-image": {"type": "docker", "image": "dummy/dummy"},
        "inputs": [],
        "output-files": [
            {
                "id": "dummy_output",
                "name": "Dummy output",
                "path-template": "dummy_output.txt",
            }
        ]
        if dummy_output
        else [],
    }

    dummy.update(descriptor)
    return dummy


def test_positional_string_arg() -> None:
    """Positional string argument."""
    settings = styx.compiler.settings.CompilerSettings(
        defs_mode=styx.compiler.settings.DefsMode.IMPORT
    )
    model = styx.boutiques.utils.boutiques_from_dict(
        _boutiques_dummy(
            {
                "command-line": "dummy [X]",
                "inputs": [
                    {
                        "id": "x",
                        "name": "The x",
                        "value-key": "[X]",
                        "type": _BT_TYPE_STRING,
                    }
                ],
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = _dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "my_string"]


def test_positional_number_arg() -> None:
    """Positional number argument."""
    settings = styx.compiler.settings.CompilerSettings(
        defs_mode=styx.compiler.settings.DefsMode.IMPORT
    )
    model = styx.boutiques.utils.boutiques_from_dict(
        _boutiques_dummy(
            {
                "command-line": "dummy [X]",
                "inputs": [
                    {
                        "id": "x",
                        "name": "The x",
                        "value-key": "[X]",
                        "type": _BT_TYPE_NUMBER,
                    }
                ],
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = _dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="123")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "123"]


def test_positional_file_arg() -> None:
    """Positional file argument."""
    settings = styx.compiler.settings.CompilerSettings(
        defs_mode=styx.compiler.settings.DefsMode.IMPORT
    )
    model = styx.boutiques.utils.boutiques_from_dict(
        _boutiques_dummy(
            {
                "command-line": "dummy [X]",
                "inputs": [
                    {
                        "id": "x",
                        "name": "The x",
                        "value-key": "[X]",
                        "type": _BT_TYPE_FILE,
                    }
                ],
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = _dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="/my/file.txt")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "/my/file.txt"]


def test_flag_arg() -> None:
    """Flag argument."""
    settings = styx.compiler.settings.CompilerSettings(
        defs_mode=styx.compiler.settings.DefsMode.IMPORT
    )
    model = styx.boutiques.utils.boutiques_from_dict(
        _boutiques_dummy(
            {
                "command-line": "dummy [X]",
                "inputs": [
                    {
                        "id": "x",
                        "name": "The x",
                        "value-key": "[X]",
                        "type": _BT_TYPE_FLAG,
                        "command-line-flag": "-x",
                    }
                ],
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = _dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "-x"]


def test_named_arg() -> None:
    """Named argument."""
    settings = styx.compiler.settings.CompilerSettings(
        defs_mode=styx.compiler.settings.DefsMode.IMPORT
    )
    model = styx.boutiques.utils.boutiques_from_dict(
        _boutiques_dummy(
            {
                "command-line": "dummy [X]",
                "inputs": [
                    {
                        "id": "x",
                        "name": "The x",
                        "value-key": "[X]",
                        "type": _BT_TYPE_STRING,
                        "command-line-flag": "-x",
                    }
                ],
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = _dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "-x", "my_string"]


def test_list_of_strings_arg() -> None:
    """List of strings."""
    settings = styx.compiler.settings.CompilerSettings(
        defs_mode=styx.compiler.settings.DefsMode.IMPORT
    )
    model = styx.boutiques.utils.boutiques_from_dict(
        _boutiques_dummy(
            {
                "command-line": "dummy [X]",
                "inputs": [
                    {
                        "id": "x",
                        "name": "The x",
                        "value-key": "[X]",
                        "type": _BT_TYPE_STRING,
                        "list": True,
                    }
                ],
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = _dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    test_module.dummy(runner=dummy_runner, x=["my_string1", "my_string2"])

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "my_string1 my_string2"]
