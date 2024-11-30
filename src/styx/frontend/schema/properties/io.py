from typing import Annotated, Any, Literal, Optional, Self, Union

import pydantic

from .. import StringProperty
from .groups import Group


class IOModel(pydantic.BaseModel):
    """Base input / output model."""

    id: Annotated[
        str, pydantic.StringConstraints(pattern=r"^[0-9,_,a-z,A-Z]*$", min_length=1)
    ] = pydantic.Field(
        description='A short, unique, informative identifier containing only alphanumeric characters and underscores. Typically used to generate variable names. Example: "data_file".',
    )
    name: StringProperty = pydantic.Field(
        description="A human-readable name. Example: 'Data file'.",
    )
    description: Optional[str] = pydantic.Field(default=None)
    list_: bool = pydantic.Field(
        alias="list",
        description='True if list of values. If value is of type "Flag" cannot be a list.',
        default=False,
    )
    optional: bool = pydantic.Field(description="True if optional", default=False)
    command_line_flag: Optional[str] = pydantic.Field(
        alias="command-line-flag",
        description='Option flag, involved in the value-key substitution. Inputs of type "Flag" have to have a command-line flag. Examples: -v, --force.',
        default=None,
    )
    command_line_flag_separator: Optional[str] = pydantic.Field(
        alias="command-line-flag-separator",
        description="Separator used between flags and their arguments. Defaults to a single space.",
        default=None,
    )
    uses_absolute_path: bool = pydantic.Field(
        alias="uses-absolute-path",
        description="Specifies value must be given as an absolute path.",
        default=False,
    )

    @pydantic.model_validator(mode="after")
    def validate_dependencies(self) -> Self:
        if self.command_line_flag_separator and not self.command_line_flag:
            raise ValueError(
                "'command-line-flag-separator' requires 'command-line-flag"
            )
        return self


class SubInput(pydantic.BaseModel):
    """Model for complex input type with sub-command details."""

    id: Annotated[str, pydantic.StringConstraints(pattern=r"^[0-9,_,a-z,A-Z]+$")]
    name: str
    description: Optional[str] = pydantic.Field(default=None)
    command_line: Optional[str] = pydantic.Field(alias="command-line", default=None)
    inputs: Optional[list["Input"]] = pydantic.Field(
        description="An array of input objects.", default=None
    )
    output_files: Optional[list[dict[str, Any]]] = pydantic.Field(
        alias="output-files", default=None
    )
    groups: Optional[list[Group]] = pydantic.Field(default=None)


class Input(IOModel):
    """Model representing a Boutiques input."""

    type_: Union[
        Literal["String", "File", "Flag", "Number"], SubInput, list[SubInput]
    ] = pydantic.Field(alias="type")
    list_separator: Optional[str] = pydantic.Field(
        alias="list-separator",
        description="Separator used between list items. Defaults to a single space.",
        default=None,
    )
    requires_inputs: Optional[list[str]] = pydantic.Field(
        alias="requires-inputs",
        description="Ids of the inputs or ids of groups whose members must be active for this input to be available.",
        default=None,
    )
    disables_inputs: Optional[list[str]] = pydantic.Field(
        alias="disables-inputs",
        description="Ids of the inputs that are disabled when this input is active.",
        default=None,
    )
    value_choices: Optional[list[Union[str, int]]] = pydantic.Field(
        alias="value-choices",
        description="Permitted choices for input value. May not be used with the Flag type.",
        default=None,
    )
    value_key: str = pydantic.Field(
        alias="value-key",
        description="A string contained in command-line, substituted by the input value and/or flag at runtime.",
    )
    value_requires: Optional[Any] = pydantic.Field(
        description="Ids of the inputs that are required when the corresponding value choice is selected.",
        default=None,
        deprecated=True,
    )
    value_enables: Optional[Any] = pydantic.Field(
        description="Ids of the inputs that are enabled when the corresponding value choice is selected.",
        default=None,
        deprecated=True,
    )
    value_disables: Optional[Any] = pydantic.Field(
        description="Ids of the inputs that are disabled when the corresponding value choice is selected.",
        default=None,
        deprecated=True,
    )
    integer: bool = pydantic.Field(
        description="Specify whether the input should be an integer. May only be used with Number type inputs.",
        default=False,
    )
    minimum: Optional[float] = pydantic.Field(
        description="Specify the minimum value of the input (inclusive). May only be used with Number type inputs.",
        default=None,
    )
    maximum: Optional[float] = pydantic.Field(
        description="Specify the maximum value of the input (inclusive). May only be used with Number type inputs.",
        default=None,
    )
    exclusive_minimum: bool = pydantic.Field(
        alias="exclusive-minimum",
        description="Specify whether the minimum is exclusive or not. May only be used with Number type inputs.",
        default=False,
    )
    exclusive_maximum: bool = pydantic.Field(
        alias="exclusive-maximum",
        description="Specify whether the maximum is exclusive or not. May only be used with Number type inputs.",
        default=False,
    )
    min_list_entries: Optional[float] = pydantic.Field(
        alias="min-list-entries",
        description="Specify the minimum number of entries in the list. May only be used with List type inputs.",
        default=None,
    )
    max_list_entries: Optional[float] = pydantic.Field(
        alias="max-list-entries",
        description="Specify the maximum number of entries in the list. May only be used with List type inputs.",
        default=None,
    )
    resolve_parent: bool = pydantic.Field(
        alias="resolve-parent",
        description="Specifies that the full parent directory of this file needs to be visible to the tool. Only specifiable for File type inputs.",
        default=False,
    )
    mutable: bool = pydantic.Field(
        description="Specifies that the tool may modify the input file. Only specifiable for File type inputs.",
        default=False,
    )

    @pydantic.field_validator("type_")
    def validate_type(cls, v):
        """Validate input type constraints."""
        if isinstance(v, str) and v not in ["String", "File", "Flag", "Number"]:
            raise ValueError(f"Invalid input type: {v}")
        return v

    @pydantic.model_validator(mode="after")
    def validate_dependencies(self) -> Self:
        if self.type_ == "Flag" and self.list_:
            raise ValueError("'list' cannot be true when input is of type 'Flag'")

        def _raise_field_error(field: str, condition: str):
            """Helper to raise field-related errors."""
            raise ValueError(f"Field '{field}' {condition}")

        if not self.list_:
            if self.min_list_entries is not None or self.max_list_entries is not None:
                _raise_field_error(
                    "min_list_entries / max_list_entries",
                    "can only be set if 'list' is true.",
                )
            if self.list_separator:
                _raise_field_error(
                    "list_separator", "can only be set if 'list_' is true."
                )

        if self.type_ != "Number":
            if self.minimum is not None or self.maximum is not None:
                _raise_field_error(
                    "minimum / maximum ",
                    "can only be set if 'type' is 'Number'.",
                )

        if self.uses_absolute_path and self.type_ != "File":
            _raise_field_error(
                "uses_absolute_path", "can only be set if 'type' is 'File'."
            )

        for excl_field, bound_field in [
            (self.exclusive_minimum, self.minimum),
            (self.exclusive_maximum, self.maximum),
        ]:
            if excl_field and bound_field is None:
                _raise_field_error(
                    "exclusive_minimum / exclusive_maximum",
                    "can only be set if minimum / maximum are provided.",
                )

        return self


class PathProperty(pydantic.BaseModel):
    """Model representing an path property."""

    propertyNames: Annotated[
        str, pydantic.StringConstraints(pattern=r"^[A-Za-z0-9_><=!)( ]*$")
    ] = pydantic.Field(default=None)


class Output(IOModel):
    """Model representing an output file."""

    path_template: Optional[StringProperty] = pydantic.Field(
        alias="path-template",
        description='Describes the output file path relatively to the execution directory. May contain input value keys and wildcards. Example: "results/[INPUT1]_brain*.mnc".',
        default=None,
    )
    conditional_path_template: Optional[list[PathProperty]] = pydantic.Field(
        alias="conditional-path-template",
        description='List of objects containing boolean statement (Limited python syntax: ==, !=, <, >, <=, >=, and, or) and output file paths relative to the execution directory, assign path of first true boolean statement. May contain input value keys, "default" object required if "optional" set to True . Example list: "[{"[PARAM1] > 8": "outputs/[INPUT1].txt"}, {"default": "outputs/default.txt"}]".',
        min_length=1,
        default=None,
    )
    path_template_stripped_extensions: Optional[list[str]] = pydantic.Field(
        alias="path-template-stripped-extensions",
        description='List of file extensions that will be stripped from the input values before being substituted in the path template. Example: [".nii",".nii.gz"].',
        default=None,
    )
    file_template: Optional[list[StringProperty]] = pydantic.Field(
        alias="file-template",
        description="An array of strings that may contain value keys. Each item will be a line in the configuration file.",
        default=None,
    )
    value_key: Optional[str] = pydantic.Field(
        alias="value-key",
        description="A string contained in command-line, substituted by the input value and/or flag at runtime.",
        default=None,
    )

    @pydantic.model_validator(mode="after")
    def validate_dependencies(self) -> Self:
        if self.path_template and self.conditional_path_template:
            raise ValueError(
                "Only one of 'path-template' or 'conditional-path-template' should be set."
            )

        if isinstance(self.file_template, list) and self.list_:
            raise ValueError(
                "If file-template' is a list, 'list' parameter should be False"
            )

        return self
