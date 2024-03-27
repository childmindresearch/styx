import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Mapping, Sequence, TypeAlias, TypeVar

T = TypeVar("T")

TYPE_INPUT_VALUE_PRIMITIVE: TypeAlias = str | float | int | bool | pathlib.Path
TYPE_INPUT_VALUE: TypeAlias = TYPE_INPUT_VALUE_PRIMITIVE | Sequence[TYPE_INPUT_VALUE_PRIMITIVE] | None
TYPE_METADATA: TypeAlias = Mapping[str, str | int | float]


class InputTypePrimitive(Enum):
    String = 1
    Number = 2
    Integer = 3
    File = 4
    Flag = 5


@dataclass
class InputType:
    primitive: InputTypePrimitive
    is_list: bool = False
    is_optional: bool = False
    is_enum: bool = False


@dataclass
class InputArgumentConstraints:
    value_min: float | int | None = None
    value_min_exclusive: bool = False
    value_max: float | int | None = None
    value_max_exclusive: bool = False
    list_length_min: int | None = None
    list_length_max: int | None = None


@dataclass
class InputArgument:
    name: str
    type: InputType
    description: str
    constraints: InputArgumentConstraints
    has_default_value: bool = False
    default_value: TYPE_INPUT_VALUE | None = None

    command_line_flag: str | None = None
    list_separator: str | None = None
    enum_values: list[TYPE_INPUT_VALUE_PRIMITIVE] | None = None

    bt_ref: str | None = None


@dataclass
class OutputArgument:
    name: str
    description: str
    path_template: str
    optional: bool = False

    stripped_file_extensions: list[str] | None = None


@dataclass
class GroupConstraint:
    name: str
    description: str
    members: list[str]

    members_mutually_exclusive: bool = False
    members_must_include_one: bool = False
    members_must_include_all_or_none: bool = False


@dataclass
class Descriptor:
    hash: str
    name: str
    description: str
    input_command_line_template: str
    inputs: list[InputArgument]
    outputs: list[OutputArgument]
    group_constraints: list[GroupConstraint]
    metadata: TYPE_METADATA


@dataclass
class WithSymbol(Generic[T]):
    data: T
    symbol: str
