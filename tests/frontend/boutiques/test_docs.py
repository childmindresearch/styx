from typing import Any

import pytest

import styx.ir.core as ir
from styx.frontend.boutiques.core import from_boutiques


class TestDocumentation:
    package_name = "My package"
    descriptor_name = "My descriptor"

    #       "name": "ANTSIntegrateVectorField",
    #   "command-line": "ANTSIntegrateVectorField [VECTOR_FIELD_INPUT] [ROI_MASK_INPUT] [FIBERS_OUTPUT] [LENGTH_IMAGE_OUTPUT]",
    #   "author": "ANTs Developers",
    #   "description": "This tool integrates a vector field, where vectors are voxels, using a region of interest (ROI) mask. The ROI mask controls where the integration is performed and specifies the starting point region.",
    #   "url": "https://github.com/ANTsX/ANTs",
    #   "tool-version": "2.5.3",
    #   "schema-version": "0.5",
    #   "inputs":

    @pytest.mark.parametrize("desc", [["A short description"], [None]])
    def test_valid_description(self, desc: str | None) -> None:
        bt = {"name": self.descriptor_name, "description": desc}
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.package.docs, ir.Documentation)
        assert out.package.docs.description == desc

    @pytest.mark.parametrize("desc", [[["A short description"]], [123]])
    @pytest.mark.skip
    def test_invalid_description_type(self, desc: Any) -> None:
        bt = {"name": self.descriptor_name, "description": desc}
        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)

    def test_valid_authors(self) -> None:
        bt = {"name": self.descriptor_name, "authors": ["Author 1", "Author 2"]}
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.package.docs.authors, list)

    # def test_descriptor(self) -> None:
    #     bt = {"name": self.descriptor_name}
    #     out = from_boutiques(bt, self.package_name)

    #     assert isinstance(out, ir.Interface)
    #     assert out.package.name == self.package_name
    #     assert isinstance(out.command.body, ir.Param.Struct)
    #     assert out.command.base.name == self.descriptor_name
