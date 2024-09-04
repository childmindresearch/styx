"""Boutiques backend."""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

import styx.ir.core as ir
from styx.frontend.boutiques.utils import boutiques_split_command

T = TypeVar("T")


def destruct_template(
    template: str,
    lookup: dict[str, T],
) -> list[str | T]:
    """Destruct a template string to a list of strings and replacements.

    This is used to safely destruct boutiques `command-line` as well as `path-template` strings.

    Example:
        >>> destruct_template(
        >>>     template="hello x, I am y",
        >>>     lookup={"x": 12, "y": 34},
        >>> )
        ["hello ", 12, ", I am ", 34]
    """
    destructed: list[str | T] = []
    stack: list[str | T] = [template]
    while len(stack) > 0:
        x = stack.pop(0)
        if not isinstance(x, str):
            destructed.append(x)
            continue
        did_split = False
        for alias, replacement in lookup.items():
            if alias in x:
                left, right = x.split(alias, 1)
                if len(right) > 0:
                    stack.insert(0, right)
                stack.insert(0, replacement)
                if len(left) > 0:
                    stack.insert(0, left)
                did_split = True
                break
        if not did_split:
            destructed.append(x)
    return destructed


@dataclass
class IdCounter:
    _counter: int = 0

    def next(self) -> int:
        self._counter += 1
        return self._counter - 1


def _hash_from_boutiques(tool: dict) -> str:
    """Generate a hash from a Boutiques tool."""
    json_str = json.dumps(tool, sort_keys=True)
    return hashlib.sha1(json_str.encode()).hexdigest()


def _bt_template_str_parse(
    input_command_line_template: str,
    lookup_input: dict[str, dict],
) -> list[list[str | dict]]:
    """Parse a Boutiques command line template string into segments."""
    bt_template_str = boutiques_split_command(input_command_line_template)
    return [destruct_template(arg, lookup_input) for arg in bt_template_str]


class InputTypePrimitive(Enum):
    String = 1
    Float = 2
    Integer = 3
    File = 4
    Flag = 5
    SubCommand = 6
    SubCommandUnion = 7


@dataclass
class InputType:
    primitive: InputTypePrimitive
    is_list: bool = False
    is_optional: bool = False
    is_enum: bool = False


def _input_type_primitive_from_boutiques(bt_input: dict) -> InputTypePrimitive:
    """Convert a Boutiques input to a Styx input type primitive."""
    if "type" not in bt_input:
        raise ValueError(f"type is missing for input: '{bt_input['id']}'")

    if isinstance(bt_input["type"], dict):
        return InputTypePrimitive.SubCommand

    if isinstance(bt_input["type"], list):
        return InputTypePrimitive.SubCommandUnion

    bt_type_name = bt_input["type"]
    if not isinstance(bt_type_name, str):
        bt_type_name = bt_type_name.value

    if bt_type_name == "String":
        return InputTypePrimitive.String
    elif bt_type_name == "File":
        return InputTypePrimitive.File
    elif bt_type_name == "Flag":
        return InputTypePrimitive.Flag
    elif bt_type_name == "Number" and not bt_input.get("integer"):
        return InputTypePrimitive.Float
    elif bt_type_name == "Number" and bt_input.get("integer"):
        return InputTypePrimitive.Integer
    else:
        raise NotImplementedError


def _input_type_from_boutiques(bt_input: dict) -> InputType:
    """Convert a Boutiques input to a Styx input type."""
    bt_is_list = bt_input.get("list") is True
    bt_is_optional = bt_input.get("optional") is True
    bt_is_enum = bt_input.get("value-choices") is not None
    primitive = _input_type_primitive_from_boutiques(bt_input)
    if primitive == InputTypePrimitive.File:
        assert not bt_is_enum
    if primitive == InputTypePrimitive.Flag:
        return InputType(InputTypePrimitive.Flag, False, True, False)
    return InputType(primitive, bt_is_list, bt_is_optional, bt_is_enum)


def _arg_elem_from_bt_elem(
    elem: dict,
    id_counter: IdCounter,
    ir_id_lookup: dict[str, ir.IdType],
) -> ir.IParam:
    if not isinstance(elem, dict):
        assert False

    d = elem

    input_bt_ref = d["value-key"]
    input_docs = ir.Documentation(
        title=d.get("name"),
        description=d.get("description"),
    )
    input_name = d["id"]

    repeatable_join: str | None = d.get("list-separator")
    input_type = _input_type_from_boutiques(d)

    input_id = id_counter.next()
    ir_id_lookup[input_bt_ref] = input_id

    dparam = ir.DParam(
        id_=input_id,
        name=input_name,
        docs=input_docs,
    )

    dlist = None
    if input_type.is_list:
        dlist = ir.DList(
            join=repeatable_join,
            count_min=d.get("min-list-entries"),
            count_max=d.get("max-list-entries"),
        )

    match input_type.primitive:
        case InputTypePrimitive.String:
            choices = d.get("value-choices")
            assert choices is None or all([
                isinstance(o, str) for o in choices
            ]), "value-choices must be all string for string input"

            if input_type.is_list:
                if input_type.is_optional:
                    return ir.PStrListOpt(
                        param=dparam,
                        list_=dlist,
                        default_value=d.get("default-value"),
                    )
                return ir.PStrList(
                    param=dparam,
                    list_=dlist,
                    default_value=d.get("default-value"),
                )
            if input_type.is_optional:
                return ir.PStrOpt(
                    param=dparam,
                    default_value=d.get("default-value"),
                    choices=choices,
                )
            return ir.PStr(
                param=dparam,
                default_value=d.get("default-value"),
                choices=choices,
            )

        case InputTypePrimitive.Integer:
            choices = d.get("value-choices")
            assert choices is None or all([
                isinstance(o, int) for o in choices
            ]), "value-choices must be all int for integer input"

            if input_type.is_list:
                if input_type.is_optional:
                    return ir.PIntListOpt(
                        param=dparam,
                        list_=dlist,
                        default_value=d.get("default-value"),
                    )
                return ir.PIntList(
                    param=dparam,
                    list_=dlist,
                    default_value=d.get("default-value"),
                )
            if input_type.is_optional:
                return ir.PIntOpt(
                    param=dparam,
                    default_value=d.get("default-value"),
                    choices=choices,
                )
            return ir.PInt(
                param=dparam,
                default_value=d.get("default-value"),
                choices=choices,
            )

        case InputTypePrimitive.Float:
            if input_type.is_list:
                if input_type.is_optional:
                    return ir.PFloatListOpt(
                        param=dparam,
                        list_=dlist,
                        default_value=d.get("default-value"),
                    )
                return ir.PFloatList(
                    param=dparam,
                    list_=dlist,
                    default_value=d.get("default-value"),
                )
            if input_type.is_optional:
                return ir.PFloatOpt(
                    param=dparam,
                    default_value=d.get("default-value"),
                )
            return ir.PFloat(
                param=dparam,
                default_value=d.get("default-value"),
            )

        case InputTypePrimitive.File:
            if input_type.is_list:
                if input_type.is_optional:
                    return ir.PFileListOpt(
                        param=dparam,
                        list_=dlist,
                    )
                return ir.PFileList(
                    param=dparam,
                    list_=dlist,
                )
            if input_type.is_optional:
                return ir.PFileOpt(
                    param=dparam,
                )
            return ir.PFile(
                param=dparam,
            )

        case InputTypePrimitive.Flag:
            input_prefix = d.get("command-line-flag")
            assert input_prefix is not None, "Flag type input must have command-line-flag"

            dparam.prefix = []
            return ir.PBool(
                param=dparam,
                default_value=d.get("default-value") is True,
                value_true=[input_prefix] if input_prefix else [],
                value_false=[],
            )
        case InputTypePrimitive.SubCommand:
            dparam, dstruct = _struct_from_boutiques(d, id_counter)
            ir_id_lookup[input_bt_ref] = dparam.id_  # override

            if input_type.is_list:
                if input_type.is_optional:
                    return ir.PStructListOpt(
                        param=dparam,
                        struct=dstruct,
                        list_=dlist,
                        default_value_set_to_none=True,
                    )
                return ir.PStructList(
                    param=dparam,
                    struct=dstruct,
                    list_=dlist,
                )
            if input_type.is_optional:
                return ir.PStructOpt(
                    param=dparam,
                    struct=dstruct,
                    default_value_set_to_none=True,
                )
            return ir.PStruct(
                param=dparam,
                struct=dstruct,
            )

        case InputTypePrimitive.SubCommandUnion:
            bt_alts = d.get("type")
            assert isinstance(bt_alts, list)

            alts: list[ir.PStruct] = []
            for bt_alt in bt_alts:
                alt_dparam, alt_dstruct = _struct_from_boutiques(bt_alt, id_counter)
                alts.append(
                    ir.PStruct(
                        param=alt_dparam,
                        struct=alt_dstruct,
                    )
                )

            if input_type.is_list:
                if input_type.is_optional:
                    return ir.PStructUnionListOpt(
                        param=dparam,
                        alts=alts,
                        list_=dlist,
                        default_value_set_to_none=True,
                    )
                return ir.PStructUnionList(
                    param=dparam,
                    alts=alts,
                    list_=dlist,
                )
            if input_type.is_optional:
                return ir.PStructUnionOpt(
                    param=dparam,
                    alts=alts,
                    default_value_set_to_none=True,
                )
            return ir.PStructUnion(
                param=dparam,
                alts=alts,
            )
    assert False


def _struct_from_boutiques(
    bt: dict,
    id_counter: IdCounter,
) -> tuple[ir.DParam, ir.DStruct]:
    def _get_authors(bt: dict) -> list[str]:
        if "author" in bt:
            return [bt["author"]]
        return []

    def _get_urls(bt: dict) -> list[str]:
        if "url" in bt:
            return [bt["url"]]
        return []

    parent_input: dict | None = None
    if "type" not in bt:  # Root boutiques descriptor
        groups, ir_id_lookup = _collect_inputs(bt, id_counter)
        outputs = _collect_outputs(bt, ir_id_lookup, id_counter)

        docs = ir.Documentation(
            description=bt.get("description"),
            authors=_get_authors(bt),
            urls=_get_urls(bt),
        )

        return ir.DParam(
            id_=id_counter.next(),
            name=bt.get("id", bt["name"]),
            outputs=outputs,
            docs=docs,
        ), ir.DStruct(
            name=bt.get("id", bt["name"]),
            groups=groups,
            docs=docs,
        )

    else:
        parent_input = bt
        bt = bt["type"]

        groups, ir_id_lookup = _collect_inputs(bt, id_counter)
        outputs = _collect_outputs(bt, ir_id_lookup, id_counter)

        docs_parent = ir.Documentation(
            description=parent_input.get("description"),
            authors=_get_authors(parent_input),
            urls=_get_urls(parent_input),
        )

        docs = ir.Documentation(
            description=bt.get("description"),
            authors=_get_authors(bt),
            urls=_get_urls(bt),
        )

        return ir.DParam(
            id_=id_counter.next(),
            name=parent_input["id"],
            outputs=outputs,
            docs=docs_parent,
        ), ir.DStruct(
            name=bt["id"],
            groups=groups,
            docs=docs,
        )


def _collect_outputs(bt, ir_id_lookup, id_counter: IdCounter):
    outputs: list[ir.Output] = []
    for bt_output in bt.get("output-files", []):
        path_template = bt_output["path-template"]
        destructed = destruct_template(path_template, ir_id_lookup)
        output_sequence = [
            ir.OutputParamReference(
                ref_id=x,
                file_remove_suffixes=bt_output.get("path-template-stripped-extensions", []),
            )
            if isinstance(x, int)
            else x
            for x in destructed
        ]
        outputs.append(
            ir.Output(
                id_=id_counter.next(),
                name=bt_output["id"],
                tokens=output_sequence,
                docs=ir.Documentation(description=bt_output.get("description")),
            )
        )
    return outputs


def _collect_inputs(bt, id_counter):
    inputs_lookup = {i["value-key"]: i for i in bt.get("inputs", [])}
    # maps boutiques 'value-keys' to expressions
    ir_id_lookup: dict[str, ir.IdType] = {}
    groups: list[ir.ConditionalGroup] = []
    for bt_segment in _bt_template_str_parse(bt.get("command-line", ""), inputs_lookup):
        group = ir.ConditionalGroup()
        carg = ir.Carg()

        for bt_elem in bt_segment:
            if isinstance(bt_elem, str):
                carg.tokens.append(bt_elem)
                continue

            param = _arg_elem_from_bt_elem(
                bt_elem,
                id_counter,
                ir_id_lookup,
            )

            if not isinstance(param, ir.IBool):
                # bool arguments use command line flag as value
                input_prefix: str | None = bt_elem.get("command-line-flag")
                input_prefix_join: str | None = bt_elem.get("command-line-flag-separator")
                if input_prefix_join is not None:
                    carg.tokens.append((input_prefix if input_prefix else "") + input_prefix_join)
                elif input_prefix:
                    group.cargs.append(ir.Carg([input_prefix]))

            carg.tokens.append(param)

        group.cargs.append(carg)
        groups.append(group)

    return groups, ir_id_lookup


def from_boutiques(tool: dict, package_name: str) -> ir.Interface:
    """Convert a Boutiques tool to a Styx descriptor."""
    if not (tool_name := tool.get("name")):
        raise ValueError(f"name is missing for tool '{tool}'")

    hash_ = _hash_from_boutiques(tool)

    docker: str | None = None
    if "container-image" in tool:
        docker = tool["container-image"].get("image")

    id_counter = IdCounter()

    dparam, dstruct = _struct_from_boutiques(tool, id_counter)

    return ir.Interface(
        uid=f"{hash_}.boutiques",
        package=ir.Package(
            name=package_name,
            version="1.0",
            docker=docker,
        ),
        command=ir.PStruct(
            param=dparam,
            struct=dstruct,
        ),
    )


if __name__ == "__main__":
    # json_path = r"C:\Users\floru\Downloads\bet.json"
    json_path = r"C:\Users\floru\Downloads\registration.json"
    print(json_path)
    with open(json_path, "r", encoding="utf-8") as json_file:
        json_data = json.load(json_file)
    ir_data = from_boutiques(json_data, package_name="AFNI")
    from styx.ir.pretty_print import pretty_print

    pretty_print(ir_data)
    from styx.ir.stats import stats

    print(stats(ir_data))
    from styx.backend.python.core import to_python

    for module, module_path in to_python([ir_data]):
        print("=" * 80)
        print("File: " + ".".join(module_path))
        print("-" * 80)
        print(module.text())
