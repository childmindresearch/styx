from typing import Mapping

from styx.boutiques.utils import boutiques_split_command
from styx.compiler.compile.constraints import generate_group_constraint_validation, generate_input_constraint_validation
from styx.compiler.compile.definitions import compile_definitions
from styx.compiler.compile.outputs import compile_output_file_expr
from styx.compiler.settings import CompilerSettings, DefsMode
from styx.model.core import TYPE_INPUT_VALUE, Descriptor, InputArgument, InputTypePrimitive, WithSymbol
from styx.pycodegen.core import LineBuffer, PyArg, PyFunc, PyModule, indent
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import (
    as_py_literal,
    enquote,
    python_pascalize,
    python_screaming_snakify,
    python_snakify,
)


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


def _input_argument_to_py_arg_builder(buf: list[str], arg: WithSymbol[InputArgument]) -> None:
    """Return a Python expression that builds the command line arguments."""
    py_symbol = arg.symbol

    if arg.data.type.primitive == InputTypePrimitive.Flag:
        assert arg.data.command_line_flag is not None
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


# def _boutiques_replace_vars(s: str, key_value: dict[str, str]) -> str:
#    for k, v in key_value.items():
#        s = s.replace(k, v)
#    return s


def _generate_metadata_expr(
    buf: LineBuffer,
    metadata: Mapping[str, TYPE_INPUT_VALUE],
    py_var_metadata: str,
) -> None:
    # Metadata
    buf.extend([
        f"{py_var_metadata} = Metadata(",
        *indent([f"{k}={as_py_literal(v)}," for k, v in metadata.items()]),
        ")",
    ])


def compile_descriptor(descriptor: Descriptor, settings: CompilerSettings) -> str:
    module_scope = Scope(parent=Scope.python())
    function_scope = Scope(parent=module_scope)
    output_tuple_scope = Scope(parent=module_scope)

    mod = PyModule()

    # Module level symbols
    module_scope.add_or_die("styx")
    module_scope.add_or_die("P")
    module_scope.add_or_die("R")
    module_scope.add_or_die("Runner")
    module_scope.add_or_die("Execution")
    module_scope.add_or_die("Metadata")
    py_var_function = module_scope.add_or_dodge(python_snakify(descriptor.name))
    py_var_output_class = module_scope.add_or_dodge(f"{python_pascalize(descriptor.name)}Outputs")
    py_var_metadata = module_scope.add_or_dodge(f"{python_screaming_snakify(descriptor.name)}_METADATA")

    # Function level symbols
    py_var_runner = function_scope.add_or_die("runner")
    py_var_execution = function_scope.add_or_die("execution")
    py_var_cargs = function_scope.add_or_die("cargs")
    py_var_ret = function_scope.add_or_die("ret")

    # Function body
    buf_body: LineBuffer = []

    # Function arguments
    args: list[WithSymbol[InputArgument]] = []
    for input_ in descriptor.inputs:
        py_symbol = function_scope.add_or_dodge(python_snakify(input_.name))
        args.append(WithSymbol(input_, py_symbol))

    # Arguments
    cmd = boutiques_split_command(descriptor.input_command_line_template)
    args_lookup = {a.data.bt_ref: a for a in args}
    args_lookup_symbol = {a.symbol: a for a in args}

    pyargs = [PyArg(name="runner", type="Runner[P, R]", default=None, docstring="Command runner")]
    pyargs += [
        PyArg(
            name=arg.symbol,
            type=_input_argument_to_py_type(arg.data),
            default=as_py_literal(arg.data.default_value) if arg.data.has_default_value else None,
            docstring=arg.data.description,
        )
        for arg in args
    ]

    # Input validation
    for arg in args:
        generate_input_constraint_validation(buf_body, arg)

    for group_constraint in descriptor.group_constraints:
        generate_group_constraint_validation(buf_body, group_constraint, args_lookup_symbol)

    # Function body
    buf_body.extend([
        f"{py_var_execution} = {py_var_runner}.start_execution({py_var_metadata})",
        f"{py_var_cargs} = []",
    ])

    # Command line args building
    for segment in cmd:
        if segment in args_lookup:
            i = args_lookup[segment]
            _input_argument_to_py_arg_builder(buf_body, i)
        else:
            buf_body.append(f"{py_var_cargs}.append({enquote(segment)})")

    # Definitions
    if settings.defs_mode == DefsMode.INLINE:
        defs = [compile_definitions()]
    elif settings.defs_mode == DefsMode.IMPORT:
        defs_module_path = "styx.runners.styxdefs" if settings.defs_module_path is None else settings.defs_module_path
        defs = [f"from {defs_module_path} import *"]
    else:
        return compile_definitions()

    buf_header = []

    # Static metadata
    buf_header.extend([
        *defs,
        "",
        "",
    ])
    _generate_metadata_expr(buf_header, descriptor.metadata, py_var_metadata)

    buf_header.extend([
        "",
        "",
        f"class {py_var_output_class}(typing.NamedTuple, typing.Generic[R]):",
        *indent([
            '"""',
            f"Output object returned when calling `{py_var_function}(...)`.",
            '"""',
        ]),
    ])

    # Output files

    outputs = []
    for output in descriptor.outputs:
        py_symbol = output_tuple_scope.add_or_dodge(python_snakify(output.name))
        outputs.append(WithSymbol(output, py_symbol))

    if descriptor.outputs is not None:
        compile_output_file_expr(
            function_scope,
            buf_header,
            buf_body,
            outputs,
            args,
            py_var_output_class,
            py_var_execution,
            py_var_ret,
        )

    buf_body.extend([
        f"{py_var_execution}.run({py_var_cargs})",
        f"return {py_var_ret}",
    ])

    mod.header.extend(buf_header)

    mod.funcs.append(
        PyFunc(
            name=py_var_function,
            args=pyargs,
            return_type=f"{py_var_output_class}[R]",
            return_descr=f"NamedTuple of outputs " f"(described in `{py_var_output_class}`).",
            docstring_body=descriptor.description,
            body=buf_body,
        )
    )

    mod.imports.extend(["import typing"])
    mod.imports.sort()

    return mod.text()
