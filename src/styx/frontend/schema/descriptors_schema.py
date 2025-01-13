from typing import Annotated, Any, Literal, Optional, Union

import pydantic

from . import StringProperty, properties


class Descriptor(pydantic.BaseModel):
    """Complete Descriptor JSON schema model."""

    model_config = pydantic.ConfigDict(
        populate_by_name=True, extra="forbid", validate_assignment=True
    )

    # Required fields
    name: StringProperty = pydantic.Field(description="Tool name.")
    description: StringProperty = pydantic.Field(description="Tool description.")
    tool_version: StringProperty = pydantic.Field(
        alias="tool-version", description="Tool version."
    )
    command_line: str = pydantic.Field(
        alias="command-line",
        description='A string that describes the tool command line, where input and output values are identified by "keys". At runtime, command-line keys are substituted with flags and values.',
    )
    schema_version: Literal["0.5"] = pydantic.Field(alias="schema-version")
    inputs: list[properties.Input] = pydantic.Field(
        description="An array of input objects", min_length=1
    )

    # Optional fields
    deprecated_by_doi: Optional[Union[StringProperty, bool]] = pydantic.Field(
        alias="deprecated-by-doi",
        description="doi of the tool that deprecates the current one. May be set to 'true' if the current tool is deprecated but no specific tool deprecates it.",
        default=None,
    )
    author: Optional[StringProperty] = pydantic.Field(
        description="Tool author name(s).", default=None
    )
    url: Optional[StringProperty] = pydantic.Field(
        description="Tool URL.", default=None
    )
    descriptor_url: Optional[StringProperty] = pydantic.Field(
        alias="descriptor-url",
        description="Link to the descriptor itself (e.g. the GitHub repo where it is hosted).",
        default=None,
    )
    doi: Optional[StringProperty] = pydantic.Field(
        description="DOI of the descriptor (not of the tool itself).", default=None
    )
    shell: Optional[StringProperty] = pydantic.Field(
        description="Absolute path of the shell interpreter to use in the container (defaults to /bin/sh).",
        default=None,
    )
    tool_doi: Optional[StringProperty] = pydantic.Field(
        alias="tool-doi",
        description="DOI of the tool (not of the descriptor).",
        default=None,
    )
    container_image: Optional[properties.ContainerImage] = pydantic.Field(
        alias="container-image", default=None
    )
    environment_variables: Optional[list[properties.EnvironmentVariable]] = (
        pydantic.Field(
            alias="environment-variables",
            description="An array of key-value pairs specifying environment variable names and their values to be used in the execution environment.",
            default=None,
        )
    )
    groups: Optional[list[properties.Group]] = pydantic.Field(
        description="Sets of identifiers of inputs, each specifying an input group.",
        default=None,
        min_length=1,
    )
    tests: Optional[list[properties.TestCase]] = pydantic.Field(
        default=None, min_length=1
    )
    online_platform_urls: Optional[
        Annotated[str, pydantic.StringConstraints(pattern=r"^https?://")]
    ] = pydantic.Field(
        alias="online-platform-urls",
        description="Online platform URLs from which the tool can be executed.",
        default=None,
    )
    output_files: Optional[list[properties.Output]] = pydantic.Field(
        alias="output-files", default=None, min_length=1
    )
    suggested_resources: Optional[properties.SuggestedResources] = pydantic.Field(
        alias="suggested-resources", default=None, min_length=1
    )
    tags: Optional[dict[str, Union[str, list[str], bool]]] = pydantic.Field(
        description="A set of key-value pairs specifying tags describing the pipeline. The tag names are open, they might be more constrained in the future.",
        default=None,
    )
    error_codes: Optional[list[properties.ErrorCode]] = pydantic.Field(
        alias="error-codes",
        description="An array of key-value pairs specifying exit codes and their description. Can be used for tools to specify the meaning of particular exit codes. Exit code 0 is assumed to indicate a successful execution.",
        min_length=1,
        default=None,
    )
    custom: Optional[dict[str, Any]] = None

    @pydantic.model_validator(mode="after")
    def validate_descriptor(self):
        """Additional validation for the entire descriptor."""
        if self.schema_version != "0.5":
            raise ValueError("Only schema version 0.5 is supported")
        return self
