from styx.boutiques.utils import boutiques_split_command
from styx.compiler.compile.common import SharedSymbols
from styx.model.core import InputArgument, InputTypePrimitive, WithSymbol
from styx.pycodegen.core import LineBuffer, PyArg, PyFunc, expand, indent
from styx.pycodegen.utils import as_py_literal, enbrace, enquote


def _input_argument_to_py_type(arg: InputArgument, sub_command_types: dict[str, str]) -> str:
    """Return the Python type expression."""
    if arg.type.is_enum:
        assert arg.enum_values is not None
        assert arg.type.primitive != InputTypePrimitive.Flag
        base = f"typing.Literal[{', '.join(map(as_py_literal, arg.enum_values))}]"
    elif arg.type.primitive == InputTypePrimitive.String:
        base = "str"
    elif arg.type.primitive == InputTypePrimitive.Number:
        base = "float | int"
    elif arg.type.primitive == InputTypePrimitive.Integer:
        base = "int"
    elif arg.type.primitive == InputTypePrimitive.File:
        base = "P"
    elif arg.type.primitive == InputTypePrimitive.Flag:
        base = "bool"
    else:
        base = sub_command_types[arg.bt_ref]  # type: ignore

    if arg.type.primitive != InputTypePrimitive.Flag:
        if arg.type.is_list:
            base = f"list[{base}]"

        if arg.type.is_optional:
            base = f"{base} | None"

    return base


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
            docstring=arg.data.description,
        )
        for arg in inputs
    ]


def _codegen_var_is_set_by_user(arg: WithSymbol[InputArgument]) -> str:
    """Return a Python expression that checks if the variable is set by the user."""
    if arg.data.type.primitive == InputTypePrimitive.Flag:
        return arg.symbol
    return f"{arg.symbol} is not None"


def _codegen_var_to_str(arg: WithSymbol[InputArgument]) -> tuple[str, bool]:
    """Return a Python expression that converts the variable to a string or string array.

    Return a boolean that indicates if the expression is an array.
    """
    if arg.data.type.primitive == InputTypePrimitive.Flag:
        assert arg.data.command_line_flag is not None, "Flag input must have a command line flag"
        return enquote(arg.data.command_line_flag), False

    def _val() -> tuple[str, bool]:
        if arg.data.type.primitive == InputTypePrimitive.File:
            if arg.data.type.is_list:
                return f"[execution.input_file(f) for f in {arg.symbol}]", True
            return f"execution.input_file({arg.symbol})", False
        if arg.data.type.is_list:
            if arg.data.type.primitive == InputTypePrimitive.SubCommand:
                return f"[a for c in [s.run(execution) for s in {arg.symbol}] for a in c]", True
            if arg.data.type.primitive != InputTypePrimitive.String:
                if arg.data.list_separator is None:
                    return f"map(str, {arg.symbol})", True
                return f'"{arg.data.list_separator}".join(map(str, {arg.symbol}))', False
            if arg.data.list_separator is None:
                return arg.symbol, True
            return f'"{arg.data.list_separator}".join({arg.symbol})', False

        if arg.data.type.primitive == InputTypePrimitive.SubCommand:
            return f"{arg.symbol}.run(execution)", True
        if (
            arg.data.type.primitive == InputTypePrimitive.Number
            or arg.data.type.primitive == InputTypePrimitive.Integer
        ):
            return f"str({arg.symbol})", False
        assert arg.data.type.primitive == InputTypePrimitive.String
        return arg.symbol, False

    if arg.data.command_line_flag is not None:
        val, val_is_list = _val()
        if val_is_list:
            return enbrace(enquote(arg.data.command_line_flag) + ", *" + val, "["), True
        return enbrace(enquote(arg.data.command_line_flag) + ", " + val, "["), True
    return _val()


def _input_segment_to_py_arg_builder(buf: LineBuffer, segment: list[str | WithSymbol[InputArgument]]) -> None:
    """Return a Python expression that builds the command line arguments."""
    if len(segment) == 0:
        return

    input_args: list[WithSymbol[InputArgument]] = [i for i in segment if isinstance(i, WithSymbol)]

    indent_level = 0

    # Are there variables?
    if len(input_args) > 0:
        # Codegen: Condition: Is any variable in the segment set by the user?
        condition = []
        for arg in input_args:
            condition.append(_codegen_var_is_set_by_user(arg))
        buf.append(f"if {' or '.join(condition)}:")
        indent_level += 1

    # Codegen: Build the string
    # Codegen: Append to the command line arguments
    if len(input_args) > 1:
        # We need to check which variables are set
        statement = []
        for token in segment:
            if isinstance(token, str):
                statement.append(enquote(token))
            else:
                var, is_list = _codegen_var_to_str(token)
                assert not is_list, "List variables are not supported in this context"
                statement.append(f'{var} if {_codegen_var_is_set_by_user(token)} else ""')
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
                statement.append(token)
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

    bt_id_inputs = {input_.data.bt_ref: input_ for input_ in inputs}

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
                    value_key = bt_input.data.bt_ref
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
