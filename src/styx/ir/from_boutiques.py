"""Boutiques frontend."""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from styx.ir.core import (
    ConstantParameter,
    Documentation,
    Expression,
    ExpressionIdType,
    ExpressionSequence,
    FileParameter,
    FloatParameter,
    IntegerParameter,
    Interface,
    OutputExpressionReference,
    OutputExpressionSequence,
    StringParameter, ExpressionAlternation,
)
from styx.model.boutiques_split_command import boutiques_split_command

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
    elem: str | dict,
    id_counter: IdCounter,
    ir_id_lookup: dict[str, ExpressionIdType],
) -> Expression:
    match elem:
        case str(s):
            return Expression(
                id_=id_counter.next(),
                name=s,
                body=ConstantParameter(s),
            )
        case dict(d):
            input_bt_ref = d["value-key"]
            input_docs = Documentation(
                title=d.get("name"),
                description=d.get("description"),
            )
            input_id = d["id"]
            input_prefix: str | None = d.get("command-line-flag")
            input_prefix_join: str | None = d.get("command-line-flag-separator")
            repeatable_join: str | None = d.get("list-separator")
            input_type = _input_type_from_boutiques(d)

            match input_type.primitive:
                case InputTypePrimitive.String:
                    choices = d.get("value-choices")
                    assert choices is None or all([
                        isinstance(o, str) for o in choices
                    ]), "value-choices must be all string for string input"

                    expression = Expression(
                        id_=id_counter.next(),
                        name=input_id,
                        body=StringParameter(
                            default_value=d.get("default-value"),
                            choices=choices,
                        ),
                        repeatable=input_type.is_list,
                        repeatable_min=d.get("min-list-entries"),
                        repeatable_max=d.get("max-list-entries"),
                        repeatable_join=repeatable_join,
                        docs=input_docs,
                    )
                    if input_prefix:
                        expression = Expression(
                            id_=id_counter.next(),
                            name=input_id,
                            body=ExpressionSequence(
                                [
                                    Expression(
                                        id_=id_counter.next(), name=input_id, body=ConstantParameter(input_prefix)
                                    ),
                                    expression,
                                ],
                                join=input_prefix_join,
                            ),
                        )
                    if input_type.is_optional:
                        expression.required = False
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression

                case InputTypePrimitive.Integer:
                    choices = d.get("value-choices")
                    assert choices is None or all([
                        isinstance(o, int) for o in choices
                    ]), "value-choices must be all int for integer input"

                    expression = Expression(
                        id_=id_counter.next(),
                        name=input_id,
                        body=IntegerParameter(
                            default_value=d.get("default-value"),
                            choices=choices,
                        ),
                        repeatable=input_type.is_list,
                        repeatable_min=d.get("min-list-entries"),
                        repeatable_max=d.get("max-list-entries"),
                        repeatable_join=repeatable_join,
                        docs=input_docs,
                    )
                    if input_prefix:
                        expression = Expression(
                            id_=id_counter.next(),
                            name=input_id,
                            body=ExpressionSequence(
                                [
                                    Expression(
                                        id_=id_counter.next(), name=input_id, body=ConstantParameter(input_prefix)
                                    ),
                                    expression,
                                ],
                                join=input_prefix_join,
                            ),
                        )
                    if input_type.is_optional:
                        expression.required = False
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression

                case InputTypePrimitive.Float:
                    expression = Expression(
                        id_=id_counter.next(),
                        name=input_id,
                        body=FloatParameter(
                            default_value=d.get("default-value"),
                        ),
                        repeatable=input_type.is_list,
                        repeatable_min=d.get("min-list-entries"),
                        repeatable_max=d.get("max-list-entries"),
                        repeatable_join=repeatable_join,
                        docs=input_docs,
                    )
                    if input_prefix:
                        expression = Expression(
                            id_=id_counter.next(),
                            name=input_id,
                            body=ExpressionSequence(
                                [
                                    Expression(
                                        id_=id_counter.next(), name=input_id, body=ConstantParameter(input_prefix)
                                    ),
                                    expression,
                                ],
                                join=input_prefix_join,
                            ),
                        )
                    if input_type.is_optional:
                        expression.required = False
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression

                case InputTypePrimitive.File:
                    expression = Expression(
                        id_=id_counter.next(),
                        name=input_id,
                        body=FileParameter(),
                        repeatable=input_type.is_list,
                        repeatable_min=d.get("min-list-entries"),
                        repeatable_max=d.get("max-list-entries"),
                        repeatable_join=repeatable_join,
                        docs=input_docs,
                    )
                    if input_prefix:
                        expression = Expression(
                            id_=id_counter.next(),
                            name=input_id,
                            body=ExpressionSequence(
                                [
                                    Expression(
                                        id_=id_counter.next(), name=input_id, body=ConstantParameter(input_prefix)
                                    ),
                                    expression,
                                ],
                                join=input_prefix_join,
                            ),
                        )
                    if input_type.is_optional:
                        expression.required = False
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression

                case InputTypePrimitive.Flag:
                    assert input_prefix is not None, "Flag type input must have command-line-flag"
                    expression = Expression(
                        id_=id_counter.next(),
                        name=input_id,
                        body=ConstantParameter(input_prefix),
                        required=False,
                        docs=input_docs,
                    )
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression
                case InputTypePrimitive.SubCommand:
                    expression = _expression_from_boutiques(d.get("type"), id_counter)
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression
                case InputTypePrimitive.SubCommandUnion:
                    alternatives = d.get("type")
                    assert isinstance(alternatives, list)

                    expression = Expression(
                        id_=id_counter.next(),
                        name=input_id,
                        body=ExpressionAlternation([
                            _expression_from_boutiques(a, id_counter) for a in alternatives
                        ]),
                        #required=False,
                        docs=input_docs,
                    )
                    ir_id_lookup[input_bt_ref] = expression.id_
                    return expression
                case _:
                    assert False, "subcommands todo"


def _expression_from_boutiques(bt: dict, id_counter: IdCounter, name: str | None = None) -> Expression:
    if (name is None) and not (name := bt.get("id")):
        raise ValueError(f"id is missing for command: '{bt}'")
    if not (bt_command_line := bt.get("command-line")):
        raise ValueError(f"command-line is missing for sub-command: '{bt}'")

    inputs_lookup = {i["value-key"]: i for i in bt.get("inputs", [])}

    # maps boutiques 'value-keys' to expressions
    ir_id_lookup: dict[str, ExpressionIdType] = {}

    arg_sequence = ExpressionSequence([])

    for segment in _bt_template_str_parse(bt_command_line, inputs_lookup):
        for elem in segment:
            arg_sequence.elements.append(
                _arg_elem_from_bt_elem(
                    elem,
                    id_counter,
                    ir_id_lookup,
                )
            )

    outputs: list[OutputExpressionSequence] = []
    for bt_output in bt.get("output-files", []):
        path_template = bt_output["path-template"]
        destructed = destruct_template(path_template, ir_id_lookup)
        output_sequence = [
            OutputExpressionReference(
                id_=x,
                file_remove_suffixes=bt_output.get("path-template-stripped-extensions", []),
            )
            if isinstance(x, int)
            else ConstantParameter(value=x)
            for x in destructed
        ]
        outputs.append(
            OutputExpressionSequence(
                name=bt_output["id"],
                sequence=output_sequence,
                docs=Documentation(description=bt_output.get("description")),
            )
        )

    authors = []
    if "author" in bt:
        authors = [bt["author"]]
    urls = []
    if "url" in bt:
        urls = [bt["url"]]

    return Expression(
        id_=id_counter.next(),
        name=name,
        body=arg_sequence,
        required=not (bt.get("optional", False) is True),
        repeatable=bt.get("list", False) is True,
        repeatable_join=bt.get("list-separator"),
        outputs=outputs,
        docs=Documentation(
            description=bt.get("description"),
            authors=authors,
            urls=urls,
        ),
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

    id_counter = IdCounter()
    expression = _expression_from_boutiques(tool, id_counter, tool_name)

    return Interface(uid=f"{hash_}.boutiques", package="Package ID", expression=expression)


if __name__ == "__main__":
    json_path = r"C:\Users\floru\Downloads\bet.json"
    #json_path = r"C:\Users\floru\Downloads\registration.json"
    print(json_path)
    with open(json_path, "r", encoding="utf-8") as json_file:
        json_data = json.load(json_file)
    ir_data = interface_from_boutiques(json_data)
    from styx.ir.pretty_print import pretty_print

    pretty_print(ir_data)
    from styx.ir.stats import stats
    print(stats(ir_data))
