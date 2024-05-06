"""Input argument default value tests."""

import styx.compiler.core
import styx.compiler.settings
import styx.runners.dummy
from tests.utils.dynmodule import (
    BT_TYPE_STRING,
    boutiques_dummy,
    dynamic_module,
)


def test_default_string_arg() -> None:
    """Default string argument."""
    settings = styx.compiler.settings.CompilerSettings(defs_mode=styx.compiler.settings.DefsMode.IMPORT)
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

    compiled_module = styx.compiler.core.compile_boutiques_dict(model, settings)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = styx.runners.dummy.DummyRunner()
    test_module.dummy(runner=dummy_runner)

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "default_string"]
