import styx.ir.core as ir
from styx.frontend.boutiques.core import from_boutiques


class TestCommandLine:
    package_name = "My package"
    descriptor_name = "My descriptor"

    def test_basic(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": "hello world",
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        assert isinstance(groups[0].cargs[0].tokens[0], str)
        assert groups[0].cargs[0].tokens[0] == "hello"
        assert isinstance(groups[1].cargs[0].tokens[0], str)
        assert groups[1].cargs[0].tokens[0] == "world"

    def test_quoting(self) -> None:
        bt = {
            "name": self.descriptor_name,
            "command-line": 'hello "string with whitespace"',
        }
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.body, ir.Param.Struct)
        groups = out.command.body.groups
        assert len(groups) == 2
        assert isinstance(groups[0].cargs[0].tokens[0], str)
        assert groups[0].cargs[0].tokens[0] == "hello"
        assert isinstance(groups[1].cargs[0].tokens[0], str)
        assert groups[1].cargs[0].tokens[0] == "string with whitespace"
