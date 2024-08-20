import dataclasses
from dataclasses import dataclass
from typing import Union


@dataclass
class Documentation:
    title: str | None = None
    description: str | None = None

    authors: list[str] = dataclasses.field(default_factory=list)
    literature: list[str] | None = dataclasses.field(default_factory=list)
    urls: list[str] | None = dataclasses.field(default_factory=list)


@dataclass
class Package:
    """Metadata for software package containing command."""

    name: str
    version: str | None
    docker: str | None

    docs: Documentation = dataclasses.field(default_factory=Documentation)


PackageReferenceType = str


@dataclass
class ConstantParameter:
    value: str


@dataclass
class IntegerParameter:
    default_value: int | None = None
    choices: list[int] | None = None
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class FloatParameter:
    default_value: float | None = None
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class StringParameter:
    default_value: str | None = None
    choices: list[str] | None = None


@dataclass
class FileParameter:
    pass


ParameterType = Union[
    IntegerParameter,
    FloatParameter,
    StringParameter,
    FileParameter,
]

ExpressionIdType = int


@dataclass
class OutputExpressionReference:
    id_: ExpressionIdType
    file_remove_suffixes: list[str] = dataclasses.field(default_factory=list)


@dataclass
class ExpressionSequence:
    elements: list["Expression"]
    join: str | None = None
    """How elements should be joined. `None`: Separate arguments"""


@dataclass
class ExpressionAlternation:
    alternatives: list["Expression"]


@dataclass
class OutputExpressionSequence:
    name: str
    sequence: list[ConstantParameter | OutputExpressionReference]

    docs: Documentation = dataclasses.field(default_factory=Documentation)


ExpressionBodyType = Union[
    ExpressionSequence,
    ExpressionAlternation,
    ConstantParameter,
    ParameterType,
]


@dataclass
class Expression:
    id_: ExpressionIdType
    name: str

    # Composition instead of inheritance
    body: ExpressionBodyType

    required: bool = True
    repeatable: bool = False
    repeatable_min: int | None = None
    repeatable_max: int | None = None
    repeatable_join: str | None = None

    outputs: list[OutputExpressionSequence] = dataclasses.field(default_factory=list)

    docs: Documentation = dataclasses.field(default_factory=Documentation)


@dataclass
class Interface:
    uid: str
    package: Package | PackageReferenceType
    expression: Expression
