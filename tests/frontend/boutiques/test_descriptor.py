from typing import Any

import pytest

import styx.ir.core as ir
from styx.frontend.boutiques.core import from_boutiques


class TestPackage:
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
    def test_invalid_descriptor(self, descriptor_name: Any) -> None:  # noqa: ANN401
        bt = {"name": descriptor_name}
        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)

    @pytest.mark.parametrize("version", ("0.0.0", None))
    def test_valid_version(self, version: str | None) -> None:
        bt = {"name": self.descriptor_name, "tool-version": version}
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.package, ir.Package)
        assert out.package.name == self.package_name
        assert out.package.version == version

    @pytest.mark.parametrize("version", (1.23, ["version"]))
    @pytest.mark.skip
    def test_invalid_version_type(self, version: Any) -> None:  # noqa: ANN401
        bt = {"name": self.descriptor_name, "tool-version": version}

        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)

    @pytest.mark.parametrize("image", ("container:version", None))
    def test_valid_docker(self, image: str | None) -> None:
        bt = {"name": self.descriptor_name, "container-image": {"image": image}}
        out = from_boutiques(bt, self.package_name)
        assert isinstance(out.package, ir.Package)
        assert out.package.name == self.package_name
        assert out.package.docker == image

    @pytest.mark.parametrize("image", (123, ["list of str"]))
    @pytest.mark.skip
    def test_invalid_docker_type(self, image: Any) -> None:  # noqa: ANN401
        bt = {"name": self.descriptor_name, "container-image": {"image": image}}

        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)
