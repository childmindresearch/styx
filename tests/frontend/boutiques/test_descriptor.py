from typing import Any

import pytest

import styx.ir.core as ir
from styx.frontend.boutiques.core import from_boutiques


class TestDescriptor:
    package_name = "My package"
    descriptor_name = "My descriptor"

    def test_descriptor(self) -> None:
        bt = {"name": self.descriptor_name}
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out, ir.Interface)
        assert out.package.name == self.package_name
        assert isinstance(out.command.body, ir.Param.Struct)
        assert out.command.base.name == self.descriptor_name

    @pytest.mark.parametrize("descriptor_name", (123, ["list of str"]))
    @pytest.mark.skip
    def test_invalid_descriptor(self, descriptor_name: Any) -> None:
        bt = {"name": descriptor_name}
        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)
