import styx.ir.core as ir
from styx.frontend.boutiques.core import from_boutiques


class TestPrimitiveParams:
    """Test primitive param types.

    Main difference in primitive types between boutiques and IR are:

    - IR has separate int and float types, boutiques just "Number"
    - Boutiques "Flag" type maps to IR bool which is encoded differently.
    """

    package_name = "My package"
    descriptor_name = "My descriptor"

    def test_int(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": "dummy [X]",
            "inputs": [
                {
                    "id": "x",
                    "value-key": "[X]",
                    "type": "Number",
                    "integer": True,
                }
            ],
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        param = groups[1].cargs[0].tokens[0]
        assert isinstance(param, ir.Param)
        assert isinstance(param.body, ir.Param.Int)

    def test_float(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": "dummy [X]",
            "inputs": [
                {
                    "id": "x",
                    "value-key": "[X]",
                    "type": "Number",
                    # "integer": False, # Default is float
                }
            ],
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        param = groups[1].cargs[0].tokens[0]
        assert isinstance(param, ir.Param)
        assert isinstance(param.body, ir.Param.Float)

    def test_file(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": "dummy [X]",
            "inputs": [
                {
                    "id": "x",
                    "value-key": "[X]",
                    "type": "File",
                }
            ],
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        param = groups[1].cargs[0].tokens[0]
        assert isinstance(param, ir.Param)
        assert isinstance(param.body, ir.Param.File)

    def test_string(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": "dummy [X]",
            "inputs": [
                {
                    "id": "x",
                    "value-key": "[X]",
                    "type": "String",
                }
            ],
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        param = groups[1].cargs[0].tokens[0]
        assert isinstance(param, ir.Param)
        assert isinstance(param.body, ir.Param.String)

    def test_bool(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": "dummy [X]",
            "inputs": [
                {
                    "id": "x",
                    "value-key": "[X]",
                    "type": "Flag",
                    "command-line-flag": "--x",
                }
            ],
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        param = groups[1].cargs[0].tokens[0]
        assert isinstance(param, ir.Param)
        assert isinstance(param.body, ir.Param.Bool)
        assert param.body.value_true == ["--x"]
        assert param.body.value_false == []
        assert not param.nullable
        assert param.default_value is False  # check identity to ensure it's False and not None
