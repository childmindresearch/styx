import dataclasses
from abc import ABC
from dataclasses import dataclass
from typing import Any, Generator


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


IdType = int


@dataclass
class OutputParamReference:
    ref_id: IdType
    file_remove_suffixes: list[str] = dataclasses.field(default_factory=list)


@dataclass
class Output:
    id_: IdType
    name: str
    tokens: list[str | OutputParamReference] = dataclasses.field(default_factory=list)
    docs: Documentation | None = None


@dataclass
class DParam:
    id_: IdType
    name: str

    outputs: list[Output] = dataclasses.field(default_factory=list)

    docs: Documentation | None = None


@dataclass
class IParam(ABC):
    param: DParam


class IOptional(ABC):
    class SetToNoneAble:  # noqa
        pass

    SetToNone = SetToNoneAble()
    pass


@dataclass
class DList:
    count_min: int | None = None
    count_max: int | None = None
    join: str | None = None


@dataclass
class IList(ABC):
    list_: DList = dataclasses.field(default_factory=DList)


@dataclass
class IInt(ABC):
    choices: list[int] | None = None
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class PInt(IInt, IParam):
    default_value: int | None = None


@dataclass
class PIntOpt(IInt, IParam, IOptional):
    default_value: int | IOptional.SetToNoneAble | None = IOptional.SetToNone


@dataclass
class PIntList(IInt, IList, IParam):
    default_value: list[int] | None = None


@dataclass
class PIntListOpt(IInt, IList, IParam, IOptional):
    default_value: list[int] | IOptional.SetToNoneAble | None = IOptional.SetToNone


class IFloat(ABC):
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class PFloat(IFloat, IParam):
    default_value: float | None = None


@dataclass
class PFloatOpt(IFloat, IParam, IOptional):
    default_value: float | IOptional.SetToNoneAble | None = IOptional.SetToNone


@dataclass
class PFloatList(IFloat, IList, IParam):
    default_value: list[float] | None = None


@dataclass
class PFloatListOpt(IFloat, IList, IParam, IOptional):
    default_value: list[float] | IOptional.SetToNoneAble | None = IOptional.SetToNone


@dataclass
class IStr(ABC):
    choices: list[str] | None = None


@dataclass
class PStr(IStr, IParam):
    default_value: str | None = None


@dataclass
class PStrOpt(IStr, IParam, IOptional):
    default_value: str | IOptional.SetToNoneAble | None = IOptional.SetToNone


@dataclass
class PStrList(IStr, IList, IParam):
    default_value: list[str] | None = None


@dataclass
class PStrListOpt(IStr, IList, IParam, IOptional):
    default_value: list[str] | IOptional.SetToNoneAble | None = IOptional.SetToNone


class IFile(ABC):
    pass


@dataclass
class PFile(IFile, IParam):
    pass


@dataclass
class PFileOpt(IFile, IParam, IOptional):
    default_value_set_to_none: bool = True


@dataclass
class PFileList(IFile, IList, IParam):
    pass


@dataclass
class PFileListOpt(IFile, IList, IParam, IOptional):
    default_value_set_to_none: bool = True


@dataclass
class IBool(ABC):
    value_true: list[str] = dataclasses.field(default_factory=list)
    value_false: list[str] = dataclasses.field(default_factory=list)


@dataclass
class PBool(IBool, IParam):
    default_value: bool | None = None


@dataclass
class PBoolOpt(IBool, IParam, IOptional):
    default_value: bool | IOptional.SetToNoneAble | None = IOptional.SetToNone


@dataclass
class PBoolList(IBool, IList, IParam):
    default_value: list[bool] | None = None


@dataclass
class PBoolListOpt(IBool, IList, IParam, IOptional):
    default_value: list[bool] | IOptional.SetToNoneAble | None = IOptional.SetToNone
    value_true: list[str] = dataclasses.field(default_factory=list)
    value_false: list[str] = dataclasses.field(default_factory=list)


@dataclass
class Carg:
    tokens: list[IParam | str] = dataclasses.field(default_factory=list)

    def iter_params(self) -> Generator[IParam, Any, None]:
        for token in self.tokens:
            if isinstance(token, IParam):
                yield token


@dataclass
class ConditionalGroup:
    cargs: list[Carg] = dataclasses.field(default_factory=list)

    def iter_params(self) -> Generator[IParam, Any, None]:
        for carg in self.cargs:
            yield from carg.iter_params()


@dataclass
class DStruct:
    name: str | None = None
    groups: list[ConditionalGroup] = dataclasses.field(default_factory=list)
    """(group (cargs (join str+params)))  """
    docs: Documentation | None = None

    def iter_params(self) -> Generator[IParam, Any, None]:
        for group in self.groups:
            yield from group.iter_params()


@dataclass
class IStruct(ABC):
    struct: DStruct = dataclasses.field(default_factory=DStruct)


@dataclass
class PStruct(IStruct, IParam):
    pass


@dataclass
class PStructOpt(IStruct, IParam, IOptional):
    default_value_set_to_none: bool = True


@dataclass
class PStructList(IStruct, IList, IParam):
    pass


@dataclass
class PStructListOpt(IStruct, IList, IParam, IOptional):
    default_value_set_to_none: bool = True


@dataclass
class IStructUnion(ABC):
    alts: list[PStruct] = dataclasses.field(default_factory=list)


@dataclass
class PStructUnion(IStructUnion, IParam):
    pass


@dataclass
class PStructUnionOpt(IStructUnion, IParam, IOptional):
    default_value_set_to_none: bool = True


@dataclass
class PStructUnionList(IStructUnion, IList, IParam):
    pass


@dataclass
class PStructUnionListOpt(IStructUnion, IList, IParam, IOptional):
    default_value_set_to_none: bool = True


@dataclass
class Interface:
    uid: str
    package: Package
    command: PStruct
