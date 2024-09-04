"""Test command line argument building."""

import tests.utils.dummy_runner
from tests.utils.compile_boutiques import boutiques2python
from tests.utils.dynmodule import (
    BT_TYPE_FILE,
    BT_TYPE_FLAG,
    BT_TYPE_NUMBER,
    BT_TYPE_STRING,
    boutiques_dummy,
    dynamic_module,
)


def test_positional_string_arg() -> None:
    """Positional string argument."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_STRING,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "my_string"]


def test_positional_number_arg() -> None:
    """Positional number argument."""
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
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="123")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "123"]


def test_positional_file_arg() -> None:
    """Positional file argument."""
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
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="/my/file.txt")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "/my/file.txt"]


def test_flag_arg() -> None:
    """Flag argument."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_FLAG,
                "command-line-flag": "-x",
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "-x"]


def test_named_arg() -> None:
    """Named argument."""
    model = boutiques_dummy({
        "command-line": "dummy [X]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_STRING,
                "command-line-flag": "-x",
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "-x", "my_string"]


def test_list_of_strings_arg() -> None:
    """List of strings."""
    model = boutiques_dummy({
        "command-line": "dummy [X] [Y]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_STRING,
                "list": True,
                "list-separator": None,
            },
            {
                "id": "y",
                "name": "The y",
                "value-key": "[Y]",
                "type": BT_TYPE_STRING,
                "list": True,
                "list-separator": " ",
            },
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x=["my_string1", "my_string2"], y=["my_string3", "my_string4"])

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["dummy", "my_string1", "my_string2", "my_string3 my_string4"]


def test_list_of_numbers_arg() -> None:
    """List of numbers."""
    model = boutiques_dummy({
        "command-line": "dummy [X] [Y]",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_NUMBER,
                "list": True,
                "list-separator": None,
            },
            {
                "id": "y",
                "name": "The y",
                "value-key": "[Y]",
                "type": BT_TYPE_NUMBER,
                "list": True,
                "list-separator": " ",
            },
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x=[1, 2], y=[3, 4])

    assert dummy_runner.last_cargs is not None
    print(compiled_module)
    assert dummy_runner.last_cargs == ["dummy", "1", "2", "3 4"]


def test_static_args() -> None:
    """Static arguments."""
    model = boutiques_dummy({
        "command-line": "dummy -a 1 -b 2 [X] -c 3 -d 4",
        "inputs": [
            {
                "id": "x",
                "name": "The x",
                "value-key": "[X]",
                "type": BT_TYPE_STRING,
            }
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy(runner=dummy_runner, x="my_string")

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == [
        "dummy",
        "-a",
        "1",
        "-b",
        "2",
        "my_string",
        "-c",
        "3",
        "-d",
        "4",
    ]


def test_arg_order() -> None:
    """Argument order.

    The wrapper should respect the order of the arguments
    in the Boutiques descriptor input array.
    """
    model = boutiques_dummy({
        "command-line": "[B] [A]",
        "inputs": [
            {
                "id": "a",
                "name": "The a",
                "value-key": "[A]",
                "type": BT_TYPE_STRING,
            },
            {
                "id": "b",
                "name": "The b",
                "value-key": "[B]",
                "type": BT_TYPE_STRING,
            },
        ],
    })

    compiled_module = boutiques2python(model)

    test_module = dynamic_module(compiled_module, "test_module")
    dummy_runner = tests.utils.dummy_runner.DummyRunner()
    test_module.dummy("aaa", "bbb", runner=dummy_runner)

    assert dummy_runner.last_cargs is not None
    assert dummy_runner.last_cargs == ["bbb", "aaa"]
