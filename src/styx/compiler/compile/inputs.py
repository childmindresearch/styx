from styx.boutiques.utils import boutiques_split_command
from styx.compiler.compile.common import SharedSymbols
from styx.model.core import Descriptor, InputArgument, InputTypePrimitive, WithSymbol
from styx.pycodegen.core import LineBuffer, PyArg, PyFunc, indent
from styx.pycodegen.utils import as_py_literal, enquote


def _input_argument_to_py_type(arg: InputArgument) -> str:
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
        raise NotImplementedError

    if arg.type.primitive != InputTypePrimitive.Flag:
        if arg.type.is_list:
            base = f"list[{base}]"

        if arg.type.is_optional:
            base = f"{base} | None"

    return base


def build_input_arguments(
    inputs: list[WithSymbol[InputArgument]],
) -> list[PyArg]:
    """Build Python function arguments from input arguments."""
    return [
        PyArg(
            name=arg.symbol,
            type=_input_argument_to_py_type(arg.data),
            default=as_py_literal(arg.data.default_value) if arg.data.has_default_value else None,
            docstring=arg.data.description,
        )
        for arg in inputs
    ]


def _input_argument_to_py_arg_builder(buf: LineBuffer, arg: WithSymbol[InputArgument]) -> None:
    """Return a Python expression that builds the command line arguments."""
    py_symbol = arg.symbol

    if arg.data.type.primitive == InputTypePrimitive.Flag:
        assert arg.data.command_line_flag is not None, "Flag input must have a command line flag"
        buf.extend([
            f"if {py_symbol}:",
            *indent([f"cargs.append({enquote(arg.data.command_line_flag)})"]),
        ])
        return

    lvl = 0

    if arg.data.type.is_optional:
        buf.append(f"if {py_symbol} is not None:")
        lvl += 1

    if arg.data.type.primitive == InputTypePrimitive.File:
        py_symbol = f"execution.input_file({py_symbol})"

    if arg.data.type.is_list:
        if arg.data.type.primitive != InputTypePrimitive.String:
            py_symbol = f"map(str, {py_symbol})"
        py_symbol = f'"{arg.data.list_separator}".join({py_symbol})'

    if arg.data.command_line_flag:
        if arg.data.type.primitive != InputTypePrimitive.String:
            py_symbol = f"str({py_symbol})"
        buf.extend(
            indent(
                [f"cargs.extend([{enquote(arg.data.command_line_flag)}, {py_symbol}])"],
                lvl,
            )
        )
    else:
        if arg.data.type.primitive == InputTypePrimitive.Number:
            py_symbol = f"str({py_symbol})"
        buf.extend(indent([f"cargs.append({py_symbol})"], lvl))


def generate_command_line_args_building(
    descriptor: Descriptor,
    symbols: SharedSymbols,
    func: PyFunc,
    inputs: list[WithSymbol[InputArgument]],
) -> None:
    """Generate the command line arguments building code."""
    # Lookup input from boutiques template reference
    inputs_lookup_bt_ref = {a.data.bt_ref: a for a in inputs}

    cmd = boutiques_split_command(descriptor.input_command_line_template)
    for segment in cmd:
        if segment in inputs_lookup_bt_ref:
            i = inputs_lookup_bt_ref[segment]
            _input_argument_to_py_arg_builder(func.body, i)
        else:
            func.body.append(f"{symbols.cargs}.append({enquote(segment)})")
