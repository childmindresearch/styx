import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Union

from styx.ir.core import (
    Command,
    Package,
    Interface,
    ArgSequence,
    ConstantParameter,
    ParameterType,
    StringParameter,
    IntegerParameter,
    FloatParameter,
    FileParameter,
)
from styx.model.boutiques_split_command import boutiques_split_command


def _hash_from_boutiques(tool: dict) -> str:
    """Generate a hash from a Boutiques tool."""
    json_str = json.dumps(tool, sort_keys=True)
    return hashlib.sha1(json_str.encode()).hexdigest()


def _bt_template_str_parse(
        input_command_line_template: str,
        lookup_input: dict[str, dict],
) -> list[list[str | dict]]:
    """Parse a Boutiques command line template string into segments."""
    _InputType = dict

    bt_template_str = boutiques_split_command(input_command_line_template)

    segments: list[list[str | _InputType]] = []

    for arg in bt_template_str:
        segment: list[str | _InputType] = []

        stack: list[str | _InputType] = [arg]

        # turn template into segments
        while stack:
            token = stack.pop()
            if isinstance(token, str):
                any_match = False
                for template_key, bt_input in lookup_input.items():
                    if template_key == token:
                        stack.append(bt_input)
                        any_match = True
                        break
                    o = token.split(template_key, 1)
                    if len(o) == 2:
                        stack.append(o[0])
                        stack.append(bt_input)
                        stack.append(o[1])
                        any_match = True
                        break
                if not any_match:
                    segment.insert(0, token)
            elif isinstance(token, _InputType):
                segment.insert(0, token)
            else:
                assert False
        segments.append(segment)

    return segments


class InputTypePrimitive(Enum):
    String = 1
    Number = 2
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
        return InputTypePrimitive.Number
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


def _arg_elem_from_bt_segment(segment: list[str | dict]) -> Union[ConstantParameter, ParameterType, Command]:
    match segment:
        case [str(s)]:
            return ConstantParameter(s)
        case [dict(d)]:
            input_description = d.get("description")
            input_type = _input_type_from_boutiques(d)
            match input_type.primitive:
                case InputTypePrimitive.String:
                    return StringParameter(d["id"], description=input_description)
                case InputTypePrimitive.Integer:
                    return IntegerParameter(d["id"], description=input_description)
                case InputTypePrimitive.Number:
                    return FloatParameter(d["id"], description=input_description)
                case InputTypePrimitive.File:
                    return FileParameter(d["id"], description=input_description)
                case InputTypePrimitive.Flag:
                    return Command(d["id"], args=ArgSequence([ConstantParameter(d["command-line-flag"])]), required=False, description=input_description)
                case _:
                    assert False, "subcommands todo"
        case _:
            pass


def _command_from_boutiques(bt: dict, name: str | None = None):
    if (name is None) and not (name := bt.get("id")):
        raise ValueError(f"id is missing for command: '{bt}'")
    if not (bt_command_line := bt.get("command-line")):
        raise ValueError(f"command-line is missing for sub-command: '{bt}'")

    inputs_lookup = {
        i["value-key"]: i for i in bt.get("inputs", [])
    }

    arg_sequence = ArgSequence([])

    for segment in _bt_template_str_parse(bt_command_line, inputs_lookup):
        arg_sequence.elements.append(_arg_elem_from_bt_segment(segment))

    authors = []
    if "author" in bt:
        authors = [bt["author"]]
    urls = []
    if "url" in bt:
        urls = [bt["url"]]

    return Command(
        name=name,
        args=arg_sequence,
        description=bt.get("description"),
        authors=authors,
        urls=urls,
    )


def interface_from_boutiques(tool: dict) -> Interface:
    """Convert a Boutiques tool to a Styx descriptor."""
    if not (tool_name := tool.get("name")):
        raise ValueError(f"name is missing for tool '{tool}'")

    hash_ = _hash_from_boutiques(tool)

    # todo
    # docker = None
    # if "container-image" in tool:
    #    docker = tool["container-image"].get("index")

    command = _command_from_boutiques(tool, tool_name)

    return Interface(
        uid=f"{hash_}.boutiques",
        package="Package ID",
        command=command
    )


if __name__ == "__main__":
    json_path = r"C:\Users\floru\Downloads\bet.json"
    with open(json_path, "r", encoding="utf-8") as json_file:
        json_data = json.load(json_file)
    ir_data = interface_from_boutiques(json_data)
    from styx.ir.pretty_print import pretty_print

    pretty_print(ir_data)
