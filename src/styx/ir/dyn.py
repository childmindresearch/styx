"""Convenience function that allows dynamic param class creation."""

import dataclasses
import typing

import styx.ir.core as ir


def dyn_param(
    dyn_type: typing.Literal["int", "float", "str", "file", "bool", "struct", "struct_union"],
    dyn_list: bool,
    dyn_optional: bool,
    **kwargs,  # noqa
) -> ir.IParam:
    """Convenience function that allows dynamic param class creation."""
    cls = {
        ("int", True, True): ir.PIntListOpt,
        ("int", True, False): ir.PIntList,
        ("int", False, True): ir.PIntOpt,
        ("int", False, False): ir.PInt,
        ("float", True, True): ir.PFloatListOpt,
        ("float", True, False): ir.PFloatList,
        ("float", False, True): ir.PFloatOpt,
        ("float", False, False): ir.PFloat,
        ("str", True, True): ir.PStrListOpt,
        ("str", True, False): ir.PStrList,
        ("str", False, True): ir.PStrOpt,
        ("str", False, False): ir.PStr,
        ("file", True, True): ir.PFileListOpt,
        ("file", True, False): ir.PFileList,
        ("file", False, True): ir.PFileOpt,
        ("file", False, False): ir.PFile,
        ("bool", True, True): ir.PBoolListOpt,
        ("bool", True, False): ir.PBoolList,
        ("bool", False, True): ir.PBoolOpt,
        ("bool", False, False): ir.PBool,
        ("struct", True, True): ir.PStructListOpt,
        ("struct", True, False): ir.PStructList,
        ("struct", False, True): ir.PStructOpt,
        ("struct", False, False): ir.PStruct,
        ("struct_union", True, True): ir.PStructUnionListOpt,
        ("struct_union", True, False): ir.PStructUnionList,
        ("struct_union", False, True): ir.PStructUnionOpt,
        ("struct_union", False, False): ir.PStructUnion,
    }[(dyn_type, dyn_list, dyn_optional)]
    kwargs_relevant = {
        field.name: kwargs[field.name] for field in dataclasses.fields(cls) if field.name if field.name in kwargs
    }
    return cls(**kwargs_relevant)
