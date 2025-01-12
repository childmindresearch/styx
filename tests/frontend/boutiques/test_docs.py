from typing import Any

import pytest

import styx.ir.core as ir
from styx.frontend.boutiques.core import from_boutiques


class TestDocumentation:
    # NOTE: 'literature' unable to be tested
    package_name = "My package"
    descriptor_name = "My descriptor"

    @pytest.mark.parametrize("desc", ("A short description", None))
    def test_valid_description(self, desc: str | None) -> None:
        bt = {"name": self.descriptor_name, "description": desc}
        out = from_boutiques(bt, self.package_name)
        assert isinstance(out.command.base.docs, ir.Documentation)
        assert out.command.base.docs.description == desc

    @pytest.mark.parametrize("desc", (["A short description"], 123))
    @pytest.mark.skip
    def test_invalid_description_type(self, desc: Any) -> None:
        bt = {"name": self.descriptor_name, "description": desc}
        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)

    # NOTE: Can only pass a single string of author(s) via boutiques
    def test_valid_authors(self) -> None:
        authors = "Author One"
        bt = {"name": self.descriptor_name, "author": authors}
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.base.docs.authors, list)
        assert out.command.base.docs.authors == [authors]

    @pytest.mark.parametrize("authors", (["Author One"], 123))
    @pytest.mark.skip
    def test_invalid_author_type(self, authors: Any) -> None:
        bt = {"name": self.descriptor_name, "author": authors}

        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)

    # NOTE: Can only pass a single string of url(s) via boutiques
    def test_valid_urls(self) -> None:
        urls = "https://url.com"
        bt = {"name": self.descriptor_name, "url": urls}
        out = from_boutiques(bt, self.package_name)

        assert isinstance(out.command.base.docs.urls, list)
        assert out.command.base.docs.urls == [urls]

    @pytest.mark.parametrize("urls", (["https://url.com"], 123))
    @pytest.mark.skip
    def test_invalid_urls_type(self, urls: Any) -> None:
        bt = {"name": self.descriptor_name, "url": urls}

        with pytest.raises(TypeError):
            from_boutiques(bt, self.package_name)
