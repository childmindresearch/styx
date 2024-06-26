"""Argument group constraint tests."""

import pytest

import styx.compiler.core
import styx.compiler.settings
import tests.utils.dummy_runner
from tests.utils.dynmodule import (
    BT_TYPE_NUMBER,
    boutiques_dummy,
    dynamic_module,
)

_XYZ_INPUTS = [
    {
        "id": "x",
        "name": "The x",
        "value-key": "[X]",
        "type": BT_TYPE_NUMBER,
        "integer": True,
        "optional": True,
    },
    {
        "id": "y",
        "name": "The y",
        "value-key": "[Y]",
        "type": BT_TYPE_NUMBER,
        "integer": True,
        "optional": True,
    },
    {
        "id": "z",
        "name": "The z",
        "value-key": "[Z]",
        "type": BT_TYPE_NUMBER,
        "integer": True,
        "optional": True,
    },
]


def test_mutually_exclusive() -> None:
    """Mutually exclusive argument group."""
    model = boutiques_dummy({
        "command-line": "dummy [X] [Y] [Z]",
        "inputs": _XYZ_INPUTS,
        "groups": [
            {
                "id": "group",
                "name": "Group",
                "members": ["x", "y", "z"],
                "mutually-exclusive": True,
            }
        ],
    })

    compiled_module = styx.compiler.core.compile_boutiques_dict(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()

    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=1, y=2)

    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=1, y=2, z=3)

    assert test_module.dummy(runner=dummy_runner, x=1) is not None
    assert test_module.dummy(runner=dummy_runner, y=2) is not None
    assert test_module.dummy(runner=dummy_runner, z=2) is not None
    assert test_module.dummy(runner=dummy_runner) is not None


def test_all_or_none() -> None:
    """All or none argument group."""
    model = boutiques_dummy({
        "command-line": "dummy [X] [Y] [Z]",
        "inputs": _XYZ_INPUTS,
        "groups": [
            {
                "id": "group",
                "name": "Group",
                "members": ["x", "y", "z"],
                "all-or-none": True,
            }
        ],
    })

    compiled_module = styx.compiler.core.compile_boutiques_dict(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=1, y=2)
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, z=3)

    assert test_module.dummy(runner=dummy_runner, x=1, y=2, z=3) is not None
    assert test_module.dummy(runner=dummy_runner) is not None


def test_one_required() -> None:
    """One required argument group."""
    model = boutiques_dummy({
        "command-line": "dummy [X] [Y] [Z]",
        "inputs": _XYZ_INPUTS,
        "groups": [
            {
                "id": "group",
                "name": "Group",
                "members": ["x", "y", "z"],
                "one-is-required": True,
            }
        ],
    })

    compiled_module = styx.compiler.core.compile_boutiques_dict(model)
    print(compiled_module)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner)

    assert test_module.dummy(runner=dummy_runner, x=1) is not None
    assert test_module.dummy(runner=dummy_runner, y=2) is not None
    assert test_module.dummy(runner=dummy_runner, z=3) is not None
    assert test_module.dummy(runner=dummy_runner, x=1, y=2) is not None
    assert test_module.dummy(runner=dummy_runner, x=1, z=3) is not None
    assert test_module.dummy(runner=dummy_runner, y=2, z=3) is not None
    assert test_module.dummy(runner=dummy_runner, x=1, y=2, z=3) is not None
