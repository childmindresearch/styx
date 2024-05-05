from styx.compiler.compile.common import SharedSymbols
from styx.compiler.compile.inputs import build_input_arguments, generate_command_line_args_building
from styx.model.core import InputArgument, InputTypePrimitive, WithSymbol
from styx.pycodegen.core import PyArg, PyDataClass, PyFunc, PyModule, blank_before
from styx.pycodegen.utils import python_pascalize, python_snakify


def _sub_command_class_name(parent_name: str, input_: WithSymbol[InputArgument]) -> str:
    """Return the name of the sub-command class."""
    return python_pascalize(f"{parent_name}_{input_.symbol}SubCommand")


def generate_sub_command(
    module: PyModule,
    symbols: SharedSymbols,
    input_: WithSymbol[InputArgument],
) -> str:
    """Generate the static output class definition."""
    class_name = _sub_command_class_name(symbols.function, input_)
    assert input_.data.sub_command is not None
    sub_command = input_.data.sub_command
    inputs_no_symbols = sub_command.inputs

    # Input symbols
    inputs: list[WithSymbol[InputArgument]] = []
    for i in inputs_no_symbols:
        # py_symbol = scopes.function.add_or_dodge(python_snakify(i.name))
        py_symbol = python_snakify(i.name)
        input_with_symbol = WithSymbol(i, py_symbol)
        inputs.append(input_with_symbol)

    sub_command_class = PyDataClass(
        name=class_name,
        docstring=f"Sub-command object for the `{input_.symbol}` argument of `{symbols.function}`.",
    )
    # generate arguments
    sub_command_class.fields.extend(build_input_arguments(inputs, {}))

    # generate run method
    run_method = PyFunc(
        name="run",
        docstring_body=f"Run the sub-command object for `{input_.symbol}`. This method is called by the main command.",
        args=[
            PyArg(name="self", type=None, default=None, docstring="The sub-command object."),
            PyArg(name="execution", type="Execution[P, R]", default=None, docstring="The execution object."),
        ],
        return_type="list[str]",
        body=[
            "cargs = []",
        ],
    )
    inputs_self = [WithSymbol(i.data, f"self.{i.symbol}") for i in inputs]
    generate_command_line_args_building(sub_command.input_command_line_template, symbols, run_method, inputs_self)
    run_method.body.extend([
        "return cargs",
    ])
    sub_command_class.methods.append(run_method)

    module.header.extend(blank_before(sub_command_class.generate(), 2))
    module.imports.append("import dataclasses")

    return class_name


def generate_sub_command_classes(
    module: PyModule,
    symbols: SharedSymbols,
    inputs: list[WithSymbol[InputArgument]],
) -> dict[str, str]:
    """Build Python function arguments from input arguments."""
    aliases: dict[str, str] = {}
    for input_ in inputs:
        if input_.data.type.primitive == InputTypePrimitive.SubCommand:
            sub_command_type = generate_sub_command(module, symbols, input_)
            if sub_command_type is not None:
                aliases[input_.data.bt_ref] = sub_command_type  # type: ignore
    return aliases
