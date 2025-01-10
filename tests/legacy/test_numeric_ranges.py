"""Numeric ranges tests."""

import pytest

import tests.legacy.utils.dummy_runner
from tests.legacy.utils.compile_boutiques import boutiques2python
from tests.legacy.utils.dynmodule import (
    BT_TYPE_NUMBER,
    boutiques_dummy,
    dynamic_module,
)


def test_below_range_minimum_inclusive() -> None:
    """Below range minimum."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
                "minimum": 5,
                "integer": True,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=4)


def test_above_range_maximum_inclusive() -> None:
    """Above range maximum."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
                "maximum": 5,
                "integer": True,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=6)


def test_above_range_maximum_exclusive() -> None:
    """Above range maximum exclusive."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
                "maximum": 5,
                "integer": True,
                "exclusive-maximum": True,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=5)


def test_below_range_minimum_exclusive() -> None:
    """Below range minimum exclusive."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
                "minimum": 5,
                "integer": True,
                "exclusive-minimum": True,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=5)


def test_outside_range() -> None:
    """Outside range."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
                "minimum": 5,
                "maximum": 10,
                "integer": True,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=11)

    with pytest.raises(ValueError):
        test_module.dummy(runner=dummy_runner, x=4)
