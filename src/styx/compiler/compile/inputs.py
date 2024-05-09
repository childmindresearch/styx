from styx.compiler.compile.common import SharedSymbols
from styx.model.boutiques_split_command import boutiques_split_command
from styx.model.core import InputArgument, InputTypePrimitive, WithSymbol
from styx.pycodegen.core import LineBuffer, PyArg, PyFunc, expand, indent
from styx.pycodegen.utils import as_py_literal, enquote


def _input_argument_to_py_type(arg: InputArgument, sub_command_types: dict[str, str]) -> str:
    """Return the Python type expression."""

    def _base() -> str:
        if arg.type.is_enum:
            assert arg.enum_values is not None
            assert arg.type.primitive != InputTypePrimitive.Flag
            assert arg.type.primitive != InputTypePrimitive.SubCommand
            return f"typing.Literal[{', '.join(map(as_py_literal, arg.enum_values))}]"

        match arg.type.primitive:
            case InputTypePrimitive.String:
                return "str"
            case InputTypePrimitive.Number:
                return "float | int"
            case InputTypePrimitive.Integer:
                return "int"
            case InputTypePrimitive.File:
                return "InputPathType"
            case InputTypePrimitive.Flag:
                return "bool"
            case InputTypePrimitive.SubCommand:
                assert arg.sub_command is not None
                return sub_command_types[arg.sub_command.internal_id]
            case InputTypePrimitive.SubCommandUnion:
                assert arg.sub_command_union is not None
                return f"typing.Union[{', '.join(sub_command_types[i.internal_id] for i in arg.sub_command_union)}]"
            case _:
                assert False

    if arg.type.primitive != InputTypePrimitive.Flag:
        if arg.type.is_list:
            return f"list[{_base()}]"
        if arg.type.is_optional:
            return f"{_base()} | None"
    return _base()


def build_input_arguments(
    inputs: list[WithSymbol[InputArgument]],
    sub_command_types: dict[str, str],
) -> list[PyArg]:
    """Build Python function arguments from input arguments."""
    return [
        PyArg(
            name=arg.symbol,
            type=_input_argument_to_py_type(arg.data, sub_command_types),
            default=as_py_literal(arg.data.default_value) if arg.data.has_default_value else None,
            docstring=arg.data.doc,
        )
        for arg in inputs
    ]


def codegen_var_is_set_by_user(arg: WithSymbol[InputArgument], enbrace_statement: bool = False) -> str:
    """Return a Python expression that checks if the variable is set by the user."""
    if arg.data.type.primitive == InputTypePrimitive.Flag:
        return arg.symbol
    if enbrace_statement:
        return f"({arg.symbol} is not None)"
    return f"{arg.symbol} is not None"


def _codegen_var_to_str(arg: WithSymbol[InputArgument]) -> tuple[str, bool]:
    """Return a Python expression that converts the variable to a string or string array.

    Return a boolean that indicates if the expression is an array.
    """
    if arg.data.type.primitive == InputTypePrimitive.Flag:
        assert arg.data.command_line_flag is not None, "Flag input must have a command line flag"
        return enquote(arg.data.command_line_flag), False

    def _val() -> tuple[str, bool]:
        if not arg.data.type.is_list:
            match arg.data.type.primitive:
                case InputTypePrimitive.String:
                    return arg.symbol, False
                case InputTypePrimitive.Number:
                    return f"str({arg.symbol})", False
                case InputTypePrimitive.Integer:
                    return f"str({arg.symbol})", False
                case InputTypePrimitive.File:
                    return f"execution.input_file({arg.symbol})", False
                case InputTypePrimitive.SubCommand:
                    return f"{arg.symbol}.run(execution)", True
                case InputTypePrimitive.SubCommandUnion:
                    return f"{arg.symbol}.run(execution)", True
                case _:
                    assert False

        # arg.data.type.is_list is True
        if arg.data.list_separator is None:
            match arg.data.type.primitive:
                case InputTypePrimitive.String:
                    return arg.symbol, True
                case InputTypePrimitive.Number:
                    return f"map(str, {arg.symbol})", True
                case InputTypePrimitive.Integer:
                    return f"map(str, {arg.symbol})", True
                case InputTypePrimitive.File:
                    return f"[execution.input_file(f) for f in {arg.symbol}]", True
                case InputTypePrimitive.SubCommand:
                    return f"[a for c in [s.run(execution) for s in {arg.symbol}] for a in c]", True
                case InputTypePrimitive.SubCommandUnion:
                    return f"[a for c in [s.run(execution) for s in {arg.symbol}] for a in c]", True
                case _:
                    assert False

        # arg.data.list_separator is not None
        sep_join = f"{enquote(arg.data.list_separator)}.join"
        match arg.data.type.primitive:
            case InputTypePrimitive.String:
                return f"{sep_join}({arg.symbol})", False
            case InputTypePrimitive.Number:
                return f"{sep_join}(map(str, {arg.symbol}))", False
            case InputTypePrimitive.Integer:
                return f"{sep_join}(map(str, {arg.symbol}))", False
            case InputTypePrimitive.File:
                return f"{sep_join}([execution.input_file(f) for f in {arg.symbol}])", False
            case InputTypePrimitive.SubCommand:
                return f"{sep_join}([a for c in [s.run(execution) for s in {arg.symbol}] for a in c])", False
            case InputTypePrimitive.SubCommandUnion:
                return f"{sep_join}([a for c in [s.run(execution) for s in {arg.symbol}] for a in c])", False
            case _:
                assert False

    if arg.data.command_line_flag is not None:
        val, val_is_list = _val()
        if arg.data.command_line_flag_separator is not None:
            assert not val_is_list, "List variables with non-null command_line_flag_separator are not supported"
            prefix = arg.data.command_line_flag + arg.data.command_line_flag_separator
            return f"({enquote(prefix)} + {val})", False

        if val_is_list:
            return f"[{enquote(arg.data.command_line_flag)}, *{val}]", True
        return f"[{enquote(arg.data.command_line_flag)}, {val}]", True
    return _val()


def _input_segment_to_py_arg_builder(buf: LineBuffer, segment: list[str | WithSymbol[InputArgument]]) -> None:
    """Return a Python expression that builds the command line arguments."""
    if len(segment) == 0:
        return

    input_args: list[WithSymbol[InputArgument]] = [i for i in segment if isinstance(i, WithSymbol)]

    indent_level = 0

    # Are there variables?
    if len(input_args) > 0:
        optional_segment = True
        for arg in input_args:
            if not arg.data.type.is_optional:
                optional_segment = False  # Segment will always be included
        if optional_segment:
            # Codegen: Condition: Is any variable in the segment set by the user?
            condition = []
            for arg in input_args:
                condition.append(codegen_var_is_set_by_user(arg))
            buf.append(f"if {' or '.join(condition)}:")
            indent_level += 1

    # Codegen: Build the string
    # Codegen: Append to the command line arguments
    if len(input_args) > 1:
        # We need to check which variables are set
        statement = []
        for token in segment:
            if isinstance(token, str):
                if len(token) == 0:
                    continue
                statement.append(enquote(token))
            else:
                var, is_list = _codegen_var_to_str(token)
                assert not is_list, "List variables are not supported in this context"
                if token.data.type.is_optional:
                    statement.append(f'({var} if {codegen_var_is_set_by_user(token)} else "")')
                else:
                    statement.append(var)
        buf.extend(
            indent(
                [
                    "cargs.append(",
                    *indent(expand(" +\n".join(statement))),
                    ")",
                ],
                indent_level,
            )
        )

    else:
        # We know the var has been set by the user
        if len(segment) == 1:
            if isinstance(segment[0], str):
                buf.extend(indent([f"cargs.append({enquote(segment[0])})"], indent_level))
            else:
                var, is_list = _codegen_var_to_str(segment[0])
                if is_list:
                    buf.extend(indent([f"cargs.extend({var})"], indent_level))
                else:
                    buf.extend(indent([f"cargs.append({var})"], indent_level))
            return

        statement = []
        for token in segment:
            if isinstance(token, str):
                statement.append(enquote(token))
            else:
                var, is_list = _codegen_var_to_str(token)
                assert not is_list, "List variables are not supported in this context"
                statement.append(var)

        buf.extend(
            indent(
                [
                    "cargs.append(",
                    *indent(expand(" +\n".join(statement))),
                    ")",
                ],
                indent_level,
            )
        )


def _bt_template_str_parse(
    input_command_line_template: str,
    inputs: list[WithSymbol[InputArgument]],
) -> list[list[str | WithSymbol[InputArgument]]]:
    """Parse a Boutiques command line template string into segments."""
    bt_template_str = boutiques_split_command(input_command_line_template)

    bt_id_inputs = {input_.data.template_key: input_ for input_ in inputs}

    segments: list[list[str | WithSymbol[InputArgument]]] = []

    for arg in bt_template_str:
        segment: list[str | WithSymbol[InputArgument]] = []

        stack: list[str | WithSymbol[InputArgument]] = [arg]

        # turn template into segments
        while stack:
            token = stack.pop()
            if isinstance(token, str):
                any_match = False
                for _, bt_input in bt_id_inputs.items():
                    value_key = bt_input.data.internal_id
                    if value_key == token:
                        stack.append(bt_input)
                        any_match = True
                        break
                    o = token.split(value_key, 1)
                    if len(o) == 2:
                        stack.append(o[0])
                        stack.append(bt_input)
                        stack.append(o[1])
                        any_match = True
                        break
                if not any_match:
                    segment.insert(0, token)
            elif isinstance(token, WithSymbol):
                segment.insert(0, token)
            else:
                assert False
        segments.append(segment)

    return segments


def generate_command_line_args_building(
    input_command_line_template: str,
    symbols: SharedSymbols,
    func: PyFunc,
    inputs: list[WithSymbol[InputArgument]],
) -> None:
    """Generate the command line arguments building code."""
    segments = _bt_template_str_parse(input_command_line_template, inputs)
    for segment in segments:
        _input_segment_to_py_arg_builder(func.body, segment)
