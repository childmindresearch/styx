"""Convert a Boutiques tool to a Styx descriptor."""

import hashlib
import json
import pathlib

from styx.model.core import (
    TYPE_INPUT_VALUE,
    TYPE_INPUT_VALUE_PRIMITIVE,
    Descriptor,
    GroupConstraint,
    InputArgument,
    InputArgumentConstraints,
    InputType,
    InputTypePrimitive,
    OutputArgument,
    SubCommand,
)


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


def _default_value_from_boutiques(bt_input: dict) -> tuple[bool, TYPE_INPUT_VALUE | None]:
    """Convert a Boutiques input to a Styx default value."""
    primitive = _input_type_primitive_from_boutiques(bt_input)
    default_value = bt_input.get("default-value")
    if default_value is None:
        if primitive == InputTypePrimitive.Flag:
            return True, False
        if bt_input.get("optional") is True:
            return True, None
        else:
            return False, None

    if primitive == InputTypePrimitive.File:
        assert isinstance(default_value, str), f"Expected string default-value, got {type(default_value)}"
        return True, pathlib.Path(default_value)
    elif primitive == InputTypePrimitive.String:
        assert isinstance(default_value, str), f"Expected string default-value, got {type(default_value)}"
    elif primitive == InputTypePrimitive.Number:
        assert isinstance(default_value, (int, float)), f"Expected number default-value, got {type(default_value)}"
    elif primitive == InputTypePrimitive.Integer:
        assert isinstance(default_value, int), f"Expected integer default-value, got {type(default_value)}"
    elif primitive == InputTypePrimitive.Flag:
        assert isinstance(default_value, bool), f"Expected boolean default-value, got {type(default_value)}"
    elif primitive == InputTypePrimitive.SubCommand:
        assert isinstance(default_value, str), f"Expected string default-value, got {type(default_value)}"
    else:
        raise NotImplementedError

    return True, default_value


def _constraints_from_boutiques(bt_input: dict) -> InputArgumentConstraints:
    """Convert a Boutiques input to a Styx input constraints."""
    value_min = None
    value_min_exclusive = False
    value_max = None
    value_max_exclusive = False
    list_length_min = None
    list_length_max = None

    input_type = _input_type_primitive_from_boutiques(bt_input)

    if input_type in (InputTypePrimitive.Number, InputTypePrimitive.Integer):
        if (val := bt_input.get("minimum")) is not None:
            value_min = int(val) if bt_input.get("integer") else val
            value_min_exclusive = bt_input.get("exclusive-minimum") is True
        if (val := bt_input.get("maximum")) is not None:
            value_max = int(val) if bt_input.get("integer") else val
            value_max_exclusive = bt_input.get("exclusive-maximum") is True
    if bt_input.get("list") is True:
        list_length_min = bt_input.get("min-list-entries")
        list_length_max = bt_input.get("max-list-entries")

    return InputArgumentConstraints(
        value_min=value_min,
        value_min_exclusive=value_min_exclusive,
        value_max=value_max,
        value_max_exclusive=value_max_exclusive,
        list_length_min=list_length_min,
        list_length_max=list_length_max,
    )


def _sub_command_from_boutiques(bt_subcommand: dict) -> SubCommand:
    """Convert a Boutiques input to a Styx sub-command."""
    if "id" not in bt_subcommand:
        raise ValueError(f"id is missing for sub-command: '{bt_subcommand}'")
    if "command-line" not in bt_subcommand:
        raise ValueError(f"command-line is missing for sub-command: '{bt_subcommand}'")

    inputs = []
    if "inputs" in bt_subcommand:
        for input_ in bt_subcommand["inputs"]:
            inputs.append(_input_argument_from_boutiques(input_))

    outputs = []
    if "output-files" in bt_subcommand:
        for output in bt_subcommand["output-files"]:
            outputs.append(_output_argument_from_boutiques(output))

    group_constraints = []
    if "groups" in bt_subcommand:
        for group in bt_subcommand["groups"]:
            group_constraints.append(_group_constraint_from_boutiques(group))

    return SubCommand(
        internal_id=bt_subcommand["id"],
        name=bt_subcommand["id"],
        doc=bt_subcommand.get("description", "Description missing"),
        input_command_line_template=bt_subcommand["command-line"],
        inputs=inputs,
        outputs=outputs,
        group_constraints=group_constraints,
    )


def _input_argument_from_boutiques(bt_input: dict) -> InputArgument:
    """Convert a Boutiques input to a Styx input argument."""
    if "id" not in bt_input:
        raise ValueError(f"id is missing for input: '{bt_input}'")
    if "type" not in bt_input:
        raise ValueError(f"type is missing for input '{bt_input['id']}'")
    # Do we want to automatically generate value-key from ID if missing?
    # Note: Boutiques 0.5 does not require value-key and I don't know why.
    if "value-key" not in bt_input:
        raise ValueError(f"value-key is missing for input '{bt_input['id']}'")

    type_ = _input_type_from_boutiques(bt_input)
    has_default_value, default_value = _default_value_from_boutiques(bt_input)
    constraints = _constraints_from_boutiques(bt_input)
    list_separator = bt_input.get("list-separator", None)

    enum_values: list[TYPE_INPUT_VALUE_PRIMITIVE] | None = None
    if (value_choices := bt_input.get("value-choices")) is not None:
        assert isinstance(value_choices, list)
        assert all(isinstance(value, (str, int, float)) for value in value_choices)

        if type_.primitive == InputTypePrimitive.Integer:
            enum_values = [int(value) for value in value_choices]
        else:
            enum_values = value_choices

    sub_command = None
    sub_command_union = None
    if type_.primitive == InputTypePrimitive.SubCommand:
        sub_command = _sub_command_from_boutiques(bt_input["type"])
    elif type_.primitive == InputTypePrimitive.SubCommandUnion:
        sub_command_union = [_sub_command_from_boutiques(subcommand) for subcommand in bt_input["type"]]

    return InputArgument(
        internal_id=bt_input["value-key"],
        template_key=bt_input["value-key"],
        name=bt_input["id"],
        type=type_,
        doc=bt_input.get("description", "Description missing"),
        has_default_value=has_default_value,
        default_value=default_value,
        constraints=constraints,
        command_line_flag=bt_input.get("command-line-flag"),
        command_line_flag_separator=bt_input.get("command-line-flag-separator"),
        list_separator=list_separator,
        enum_values=enum_values,
        sub_command=sub_command,
        sub_command_union=sub_command_union,
    )


def _output_argument_from_boutiques(bt_output: dict) -> OutputArgument:
    """Convert a Boutiques output to a Styx output argument."""
    if "id" not in bt_output:
        raise ValueError(f"id is missing for output: '{bt_output}'")
    if "path-template" not in bt_output:
        raise ValueError(f"path-template is missing for output '{bt_output['id']}'")

    return OutputArgument(
        name=bt_output["id"],
        doc=bt_output.get("description", "Description missing"),
        optional=bt_output.get("optional") is True,
        stripped_file_extensions=bt_output.get("path-template-stripped-extensions"),
        path_template=bt_output["path-template"],
    )


def _group_constraint_from_boutiques(bt_group: dict) -> GroupConstraint:
    """Convert a Boutiques group to a Styx group constraint."""
    if "id" not in bt_group:
        raise ValueError(f"id is missing for group: '{bt_group}'")

    return GroupConstraint(
        name=bt_group["id"],
        description=bt_group.get("description", "Description missing"),
        members=bt_group.get("members", []),  # A group without members does not make sense. Raise an error?
        members_mutually_exclusive=bt_group.get("mutually-exclusive") is True,
        members_must_include_one=bt_group.get("one-is-required") is True,
        members_must_include_all_or_none=bt_group.get("all-or-none") is True,
    )


def _hash_from_boutiques(tool: dict) -> str:
    """Generate a hash from a Boutiques tool."""
    json_str = json.dumps(tool, sort_keys=True)
    return hashlib.sha1(json_str.encode()).hexdigest()


def _boutiques_metadata(tool: dict, tool_hash: str) -> dict:
    """Extract metadata from a Boutiques tool."""
    if "name" not in tool:
        raise ValueError(f"name is missing for tool '{tool}'")

    metadata = {"id": tool_hash, "name": tool["name"]}
    if (container_image := tool.get("container-image")) is not None:
        if (val := container_image.get("type")) is not None:
            metadata["container_image_type"] = val
        if (val := container_image.get("index")) is not None:
            metadata["container_image_index"] = val
        if (val := container_image["image"]) is not None:
            metadata["container_image_tag"] = val
    return metadata


def _boutiques_documentation(tool: dict) -> str:
    """Extract documentation from a Boutiques tool."""
    if "name" not in tool:
        raise ValueError(f"name is missing for tool '{tool}'")

    doc = tool["name"]

    if "author" in tool:
        doc += f" by {tool['author']}"

    description = tool.get("description", "Description missing.")
    if not description.endswith("."):
        description += "."

    doc += f".\n\n{description}"

    if "url" in tool:
        doc += f"\n\nMore information: {tool['url']}"

    return doc


def descriptor_from_boutiques(tool: dict) -> Descriptor:
    """Convert a Boutiques tool to a Styx descriptor."""
    if "name" not in tool:
        raise ValueError(f"name is missing for tool '{tool}'")
    if "command-line" not in tool:
        raise ValueError(f"command-line is missing for tool '{tool['name']}'")

    inputs = []
    if "inputs" in tool:
        for input_ in tool["inputs"]:
            inputs.append(_input_argument_from_boutiques(input_))

    outputs = []
    if "output-files" in tool:
        for output in tool["output-files"]:
            outputs.append(_output_argument_from_boutiques(output))

    group_constraints = []
    if "groups" in tool:
        for group in tool["groups"]:
            group_constraints.append(_group_constraint_from_boutiques(group))

    hash_ = _hash_from_boutiques(tool)

    metadata = _boutiques_metadata(tool, hash_)

    return Descriptor(
        hash=hash_,
        metadata=metadata,
        command=SubCommand(
            internal_id=tool["name"],
            name=tool["name"],
            doc=_boutiques_documentation(tool),
            input_command_line_template=tool["command-line"],
            inputs=inputs,
            outputs=outputs,
            group_constraints=group_constraints,
        ),
    )
