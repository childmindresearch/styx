from dataclasses import dataclass, field
from typing import Generic, TypeVar

from styx.backend.generic.linebuffer import LineBuffer


@dataclass
class GenericArg:
    """Represents a generic argument for functions, class members, etc."""

    name: str
    """The name of the argument."""

    type: str | None = None
    """The type of the argument (optional)."""

    default: str | None = None
    """The default value of the argument (optional)."""

    docstring: str | None = None
    """The documentation string for the argument (optional)."""


_ArgType = TypeVar("_ArgType", bound=GenericArg)


@dataclass
class GenericFunc(Generic[_ArgType]):
    """Represents a generic function with arguments, body, and return information."""

    name: str
    """The name of the function."""

    args: list[_ArgType] = field(default_factory=list)
    """A list of arguments (GenericArg) for the function."""

    docstring_body: str | None = None
    """The body of the function's docstring (optional)."""

    body: LineBuffer = field(default_factory=list)
    """The content of the function's body as a LineBuffer."""

    return_descr: str | None = None
    """The description of the function's return value (optional)."""

    return_type: str | None = None
    """The type of the function's return value (optional)."""


_FuncType = TypeVar("_FuncType", bound=GenericFunc)


@dataclass
class GenericDataClass(Generic[_ArgType, _FuncType]):
    """Represents a generic data class with fields and methods."""

    name: str
    """The name of the data class."""

    docstring: str | None
    """The documentation string for the class (optional)."""

    fields: list[_ArgType] = field(default_factory=list)
    """A list of fields (GenericArg) for the data class."""

    methods: list[_FuncType] = field(default_factory=list)
    """A list of methods (GenericFunc) for the data class."""


_DataClassType = TypeVar("_DataClassType", bound=GenericDataClass)


@dataclass
class GenericNamedTuple(Generic[_ArgType, _FuncType]):
    """Represents a generic data class with fields and methods."""

    name: str
    """The name of the data class."""

    docstring: str | None
    """The documentation string for the class (optional)."""

    fields: list[_ArgType] = field(default_factory=list)
    """A list of fields (GenericArg) for the data class."""

    methods: list[_FuncType] = field(default_factory=list)
    """A list of methods (GenericFunc) for the data class."""


_NamedTupleType = TypeVar("_NamedTupleType", bound=GenericNamedTuple)


@dataclass
class GenericModule(Generic[_ArgType, _DataClassType]):
    """Represents a generic module containing functions, classes, and other elements."""

    imports: LineBuffer = field(default_factory=list)
    """A list of imports as a LineBuffer."""

    header: LineBuffer = field(default_factory=list)
    """The header of the module as a LineBuffer."""

    funcs_and_classes: list[_ArgType | _DataClassType] = field(default_factory=list)
    """A list of functions and classes within the module."""

    footer: LineBuffer = field(default_factory=list)
    """The footer of the module as a LineBuffer."""

    exports: list[str] = field(default_factory=list)
    """A list of exported symbols from the module."""

    docstr: str | None = None
    """The documentation string for the module (optional)."""
