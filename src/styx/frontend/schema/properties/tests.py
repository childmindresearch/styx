from typing import Annotated, Any, Optional

import pydantic

from .. import StringProperty


class OutputFile(pydantic.BaseModel):
    id: Annotated[
        str, pydantic.StringConstraints(pattern=r"^[0-9,_,a-z,A-Z]*$", min_length=1)
    ] = pydantic.Field(description="Id referring to an output-file")
    md5_reference: Optional[str] = pydantic.Field(
        alias="md5-reference",
        description="MD5 checksum string to match against the MD5 checksum of the output-file specified by the id object",
        min_length=1,
        default=None,
    )


class Assertion(pydantic.BaseModel):
    exit_code: int = pydantic.Field(
        alias="exit-code", description="Expected code returned by the program."
    )
    output_files: list[OutputFile] = pydantic.Field(alias="output-files", min_length=1)


class TestCase(pydantic.BaseModel):
    """Model for test cases."""

    name: StringProperty = pydantic.Field(description="Name of the test-case")
    invocation: dict[str, Any]
    assertions: Assertion
