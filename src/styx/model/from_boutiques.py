# type: ignore

import hashlib
import pathlib

from styx.boutiques import model as bt
from styx.boutiques import utils as btu
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


def _input_type_primitive_from_boutiques(bt_input: btu.InputType) -> InputTypePrimitive:
    """Convert a Boutiques input to a Styx input type primitive."""
    if isinstance(bt_input.root.type, bt.Type2):
        return InputTypePrimitive.SubCommand
    else:
        bt_type_name = bt_input.root.type
        if not isinstance(bt_type_name, str):
            bt_type_name = bt_type_name.value

    if bt_type_name == "String":
        return InputTypePrimitive.String
    elif bt_type_name == "File":
        return InputTypePrimitive.File
    elif bt_type_name == "Flag":
        return InputTypePrimitive.Flag
    elif bt_type_name == "Number" and not bt_input.root.integer:
        return InputTypePrimitive.Number
    elif bt_type_name == "Number" and bt_input.root.integer:
        return InputTypePrimitive.Integer
    else:
        raise NotImplementedError


def _input_type_from_boutiques(bt_input_: btu.InputType) -> InputType:
    """Convert a Boutiques input to a Styx input type."""
    bt_input = bt_input_.root

    bt_is_list = bt_input.list is True
    bt_is_optional = bt_input.optional is True
    bt_is_enum = bt_input.value_choices is not None
    primitive = _input_type_primitive_from_boutiques(bt_input_)
    if primitive == InputTypePrimitive.File:
        assert not bt_is_enum
    if primitive == InputTypePrimitive.Flag:
        return InputType(InputTypePrimitive.Flag, False, True, False)
    return InputType(primitive, bt_is_list, bt_is_optional, bt_is_enum)


def _default_value_from_boutiques(bt_input_: btu.InputType) -> tuple[bool, TYPE_INPUT_VALUE | None]:
    """Convert a Boutiques input to a Styx default value."""
    bt_input = bt_input_.root

    primitive = _input_type_primitive_from_boutiques(bt_input_)
    default_value = bt_input.default_value
    if default_value is None:
        if primitive == InputTypePrimitive.Flag:
            return True, False
        if bt_input.optional is True:
            return True, None
        else:
            return False, None

    if primitive == InputTypePrimitive.File:
        assert isinstance(default_value, str)
        return True, pathlib.Path(default_value)
    elif primitive == InputTypePrimitive.String:
        assert isinstance(default_value, str)
    elif primitive == InputTypePrimitive.Number:
        assert isinstance(default_value, (int, float))
    elif primitive == InputTypePrimitive.Integer:
        assert isinstance(default_value, int)
    elif primitive == InputTypePrimitive.Flag:
        assert isinstance(default_value, bool)
    elif primitive == InputTypePrimitive.SubCommand:
        assert isinstance(default_value, str)
    else:
        raise NotImplementedError

    return True, default_value


def _constraints_from_boutiques(bt_input_: btu.InputType) -> InputArgumentConstraints:
    """Convert a Boutiques input to a Styx input constraints."""
    bt_input = bt_input_.root

    value_min = None
    value_min_exclusive = False
    value_max = None
    value_max_exclusive = False
    list_length_min = None
    list_length_max = None

    input_type = _input_type_primitive_from_boutiques(bt_input_)

    if input_type in (InputTypePrimitive.Number, InputTypePrimitive.Integer):
        if bt_input.minimum is not None:
            value_min = int(bt_input.minimum) if bt_input.integer else bt_input.minimum
            value_min_exclusive = bt_input.exclusive_minimum is True
        if bt_input.maximum is not None:
            value_max = int(bt_input.maximum) if bt_input.integer else bt_input.maximum
            value_max_exclusive = bt_input.exclusive_maximum is True
    if bt_input.list is True:
        list_length_min = bt_input.min_list_entries
        list_length_max = bt_input.max_list_entries

    return InputArgumentConstraints(
        value_min=value_min,
        value_min_exclusive=value_min_exclusive,
        value_max=value_max,
        value_max_exclusive=value_max_exclusive,
        list_length_min=list_length_min,
        list_length_max=list_length_max,
    )


def _input_argument_from_boutiques(bt_input_: btu.InputType) -> InputArgument:
    """Convert a Boutiques input to a Styx input argument."""
    bt_input = bt_input_.root

    type_ = _input_type_from_boutiques(bt_input_)
    has_default_value, default_value = _default_value_from_boutiques(bt_input_)
    constraints = _constraints_from_boutiques(bt_input_)
    list_separator = bt_input.list_separator

    enum_values: list[TYPE_INPUT_VALUE_PRIMITIVE] | None = None
    if bt_input.value_choices is not None:
        assert isinstance(bt_input.value_choices, list)
        assert all(isinstance(value, (str, int, float)) for value in bt_input.value_choices)

        if type_.primitive == InputTypePrimitive.Integer:
            enum_values = [int(value) for value in bt_input.value_choices]
        else:
            enum_values = bt_input.value_choices

    if type_.primitive == InputTypePrimitive.SubCommand:
        sub_command = SubCommand(
            input_command_line_template=bt_input.type.command_line,
            inputs=[_input_argument_from_boutiques(input_) for input_ in bt_input.type.inputs],
        )
    else:
        sub_command = None

    return InputArgument(
        name=bt_input.id,
        type=type_,
        description=bt_input.description,
        has_default_value=has_default_value,
        default_value=default_value,
        constraints=constraints,
        command_line_flag=bt_input.command_line_flag,
        list_separator=list_separator,
        enum_values=enum_values,
        sub_command=sub_command,
        bt_ref=bt_input.value_key,
    )


def _output_argument_from_boutiques(bt_output: btu.OutputType) -> OutputArgument:
    """Convert a Boutiques output to a Styx output argument."""
    return OutputArgument(
        name=bt_output.id,
        description=bt_output.description,
        optional=bt_output.optional,
        stripped_file_extensions=bt_output.path_template_stripped_extensions,
        path_template=bt_output.path_template,
    )


def _group_constraint_from_boutiques(bt_group: bt.Group) -> GroupConstraint:
    """Convert a Boutiques group to a Styx group constraint."""
    return GroupConstraint(
        name=bt_group.id,
        description=bt_group.description or "Description missing",
        members=bt_group.members,
        members_mutually_exclusive=bt_group.mutually_exclusive is True,
        members_must_include_one=bt_group.one_is_required is True,
        members_must_include_all_or_none=bt_group.all_or_none is True,
    )


def descriptor_from_boutiques(tool: bt.Tool) -> Descriptor:
    """Convert a Boutiques tool to a Styx descriptor."""
    inputs = []
    for input_ in tool.inputs:
        inputs.append(_input_argument_from_boutiques(input_))

    outputs = []
    if tool.output_files is not None:
        for output in tool.output_files:
            outputs.append(_output_argument_from_boutiques(output))

    group_constraints = []
    if tool.groups is not None:
        for group in tool.groups:
            group_constraints.append(_group_constraint_from_boutiques(group))

    hash_: str = hashlib.sha1(tool.model_dump_json().encode()).hexdigest()

    metadata = {"id": hash_, "name": tool.name}
    if tool.container_image is not None:
        if tool.container_image.root.type is not None:
            metadata["container_image_type"] = tool.container_image.root.type.name
        if tool.container_image.root.index is not None:
            metadata["container_image_index"] = tool.container_image.root.index
        if tool.container_image.root.image is not None:
            metadata["container_image_tag"] = tool.container_image.root.image

    return Descriptor(
        hash=hash_,
        name=tool.name,
        description=tool.description,
        input_command_line_template=tool.command_line,
        inputs=inputs,
        outputs=outputs,
        group_constraints=group_constraints,
        metadata=metadata,
    )
