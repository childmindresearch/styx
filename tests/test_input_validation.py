"""Input validation tests.

Non-goals:
- Argument types. -> typing

Goals:
- Numeric ranges of values.
- Mutually exclusive arguments.

"""

import styx.boutiques.utils
import styx.compiler.core
import styx.compiler.settings
import styx.runners.core
from tests.utils.dynmodule import (
    BT_TYPE_NUMBER,
    boutiques_dummy,
    dynamic_module,
)


def test_below_range_minimum_inclusive() -> None:
    """Below range minimum."""
    settings = styx.compiler.settings.CompilerSettings(defs_mode=styx.compiler.settings.DefsMode.IMPORT)
    model = styx.boutiques.utils.boutiques_from_dict(
        boutiques_dummy(
            {
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
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    try:
        test_module.dummy(runner=dummy_runner, x=4)
    except ValueError as e:
        assert "must be greater than" in str(e)
    else:
        assert False, "Expected ValueError"


def test_above_range_maximum_inclusive() -> None:
    """Above range maximum."""
    settings = styx.compiler.settings.CompilerSettings(defs_mode=styx.compiler.settings.DefsMode.IMPORT)
    model = styx.boutiques.utils.boutiques_from_dict(
        boutiques_dummy(
            {
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
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    try:
        test_module.dummy(runner=dummy_runner, x=6)
    except ValueError as e:
        assert "must be less than" in str(e)
    else:
        assert False, "Expected ValueError"


def test_above_range_maximum_exclusive() -> None:
    """Above range maximum exclusive."""
    settings = styx.compiler.settings.CompilerSettings(defs_mode=styx.compiler.settings.DefsMode.IMPORT)
    model = styx.boutiques.utils.boutiques_from_dict(
        boutiques_dummy(
            {
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
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    try:
        test_module.dummy(runner=dummy_runner, x=5)
    except ValueError as e:
        assert "must be less than" in str(e)
    else:
        assert False, "Expected ValueError"


def test_below_range_minimum_exclusive() -> None:
    """Below range minimum exclusive."""
    settings = styx.compiler.settings.CompilerSettings(defs_mode=styx.compiler.settings.DefsMode.IMPORT)
    model = styx.boutiques.utils.boutiques_from_dict(
        boutiques_dummy(
            {
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
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    try:
        test_module.dummy(runner=dummy_runner, x=5)
    except ValueError as e:
        assert "must be greater than" in str(e)
    else:
        assert False, "Expected ValueError"


def test_outside_range() -> None:
    """Outside range."""
    settings = styx.compiler.settings.CompilerSettings(defs_mode=styx.compiler.settings.DefsMode.IMPORT)
    model = styx.boutiques.utils.boutiques_from_dict(
        boutiques_dummy(
            {
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
            }
        )
    )

    compiled_module = styx.compiler.core.compile_descriptor(model, settings)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.core.DummyRunner()
    try:
        test_module.dummy(runner=dummy_runner, x=11)
    except ValueError as e:
        assert "must be less than" in str(e)
    else:
        assert False, "Expected ValueError"

    try:
        test_module.dummy(runner=dummy_runner, x=4)
    except ValueError as e:
        assert "must be greater than" in str(e)
    else:
        assert False, "Expected ValueError"
