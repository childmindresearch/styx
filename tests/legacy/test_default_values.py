"""Input argument default value tests."""

import tests.legacy.utils.dummy_runner
from tests.legacy.utils.compile_boutiques import boutiques2python
from tests.legacy.utils.dynmodule import (
    BT_TYPE_STRING,
    boutiques_dummy,
    dynamic_module,
)


def test_default_string_arg() -> None:
    """Default string argument."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_STRING,
                "default-value": "default_string",
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner)

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "default_string"]
