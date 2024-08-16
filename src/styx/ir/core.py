import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional


@dataclass
class Package:
    """Metadata for software package containing command."""
    name: str
    version: str | None
    docker: str | None

    description: str | None = None
    authors: list[str] = dataclasses.field(default_factory=list)
    references: list[str] | None = dataclasses.field(default_factory=list)
    urls: list[str] | None = dataclasses.field(default_factory=list)


PackageReferenceType = str


@dataclass
class ConstantParameter:
    value: str


@dataclass
class IntegerParameter:
    name: str
    description: str | None = None


@dataclass
class FloatParameter:
    name: str
    description: str | None = None


@dataclass
class StringParameter:
    name: str
    description: str | None = None


@dataclass
class FileParameter:
    name: str
    description: str | None = None


ParameterReferenceType = str


ParameterType = Union[
    IntegerParameter,
    FloatParameter,
    StringParameter,
    FileParameter,
]


@dataclass
class ArgSequence:
    elements: list[Union[ConstantParameter, ParameterType, "Command"]]


@dataclass
class ArgUnion:
    variants: list["Command"]


@dataclass
class CommandOutput:
    name: str
    sequence: Union[ConstantParameter, ParameterReferenceType]

    description: str | None = None


@dataclass
class Command:
    name: str

    args: Union[
        ArgSequence,
        ArgUnion,
    ]

    required: bool = True
    repeatable: bool = False
    join: str | None = None
    """How args should be joined. `None`: Separate arguments"""

    outputs: list[CommandOutput] = dataclasses.field(default_factory=list)

    description: str | None = None
    authors: list[str] = dataclasses.field(default_factory=list)
    references: list[str] | None = dataclasses.field(default_factory=list)
    urls: list[str] | None = dataclasses.field(default_factory=list)


@dataclass
class Interface:
    uid: str
    package: Package | PackageReferenceType
    command: Command
