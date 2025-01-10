"""Test output file paths."""

import tests.legacy.utils.dummy_runner
from tests.legacy.utils.compile_boutiques import boutiques2python
from tests.legacy.utils.dynmodule import (
    BT_TYPE_FILE,
    BT_TYPE_NUMBER,
    boutiques_dummy,
    dynamic_module,
)


def test_output_file() -> None:
    """Test an output file."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
            }
        ],
        "output-files": [
            {
                "id": "out",
                "name": "The out",
                "path-template": "out.txt",
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    out = test_module.dummy(runner=dummy_runner, x=5)

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "5"]
    assert out is not None
    assert out.out == "out.txt"


def test_output_file_with_template() -> None:
    """Test an output file with a template."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
            }
        ],
        "output-files": [
            {
                "id": "out",
                "name": "The out",
                "path-template": "out-[X].txt",
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    out = test_module.dummy(runner=dummy_runner, x=5)

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "5"]
    assert out is not None
    assert out.out == "out-5.txt"


def test_output_file_with_template_and_stripped_extensions() -> None:
    """Test an output file with a template and stripped extensions."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_FILE,
            }
        ],
        "output-files": [
            {
                "id": "out",
                "name": "The out",
                "path-template": "out-[X].png",
                "path-template-stripped-extensions": [".txt"],
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.legacy.utils.dummy_runner.DummyRunner()
    out = test_module.dummy(runner=dummy_runner, x="in.txt")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "in.txt"]
    assert out is not None
    assert out.out == "out-in.png"
