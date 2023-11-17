"""Dynamic boutiques module creation for testing purposes."""

import importlib.util
from types import ModuleType

BT_TYPE_STRING = "String"
BT_TYPE_NUMBER = "Number"
BT_TYPE_FILE = "File"
BT_TYPE_FLAG = "Flag"


def dynamic_module(source_code: str, module_name: str) -> ModuleType:
    """Create a dynamic module."""
    module_spec = importlib.util.spec_from_loader(module_name, loader=None)
    assert module_spec is not None  # mypy
    module = importlib.util.module_from_spec(module_spec)
    exec(source_code, module.__dict__)
    # TODO: Does this module need to be unloaded somehow after use?
    return module


def boutiques_dummy(descriptor: dict) -> dict:
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
        ],
    }

    dummy.update(descriptor)
    return dummy
