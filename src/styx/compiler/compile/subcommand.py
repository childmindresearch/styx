from styx.compiler.compile.common import SharedSymbols
from styx.compiler.compile.constraints import generate_constraint_checks
from styx.compiler.compile.inputs import build_input_arguments, generate_command_line_args_building
from styx.model.core import InputArgument, InputTypePrimitive, SubCommand, WithSymbol
from styx.pycodegen.core import PyArg, PyDataClass, PyFunc, PyModule, blank_before
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import python_pascalize, python_snakify


def _sub_command_class_name(parent_name: str, sub_command: SubCommand) -> str:
    """Return the name of the sub-command class."""
    return python_pascalize(f"{parent_name}_{sub_command.name}")


def _generate_sub_command(
    module: PyModule,
    symbols: SharedSymbols,
    sub_command: SubCommand,
    inputs: list[WithSymbol[InputArgument]],
    aliases: dict[str, str],
) -> str:
    """Generate the static output class definition."""
    class_name = _sub_command_class_name(symbols.function, sub_command)

    sub_command_class = PyDataClass(
        name=class_name,
        docstring=sub_command.doc,
    )
    # generate arguments
    sub_command_class.fields.extend(build_input_arguments(inputs, aliases))

    # generate run method
    run_method = PyFunc(
        name="run",
        docstring_body="Build command line arguments. This method is called by the main command.",
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

    generate_constraint_checks(run_method, sub_command.group_constraints, inputs_self)

    generate_command_line_args_building(sub_command.input_command_line_template, symbols, run_method, inputs_self)
    run_method.body.extend([
        "return cargs",
    ])
    sub_command_class.methods.append(run_method)

    module.header.extend(blank_before(sub_command_class.generate(), 2))
    if "import dataclasses" not in module.imports:
        module.imports.append("import dataclasses")

    return class_name


def generate_sub_command_classes(
    module: PyModule,
    symbols: SharedSymbols,
    command: SubCommand,
    scope: Scope,
) -> tuple[dict[str, str], list[WithSymbol[InputArgument]]]:
    """Build Python function arguments from input arguments."""
    aliases: dict[str, str] = {}

    inputs_scope = Scope(parent=scope)
    # outputs_scope = Scope(parent=scope)

    # Input symbols
    inputs: list[WithSymbol[InputArgument]] = []
    for i in command.inputs:
        py_symbol = inputs_scope.add_or_dodge(python_snakify(i.name))
        inputs.append(WithSymbol(i, py_symbol))

    # Output symbols
    # outputs: list[WithSymbol[OutputArgument]] = []
    # for output in command.outputs:
    #    py_symbol = outputs_scope.add_or_dodge(python_snakify(output.name))
    #    outputs.append(WithSymbol(output, py_symbol))

    for input_ in inputs:
        if input_.data.type.primitive == InputTypePrimitive.SubCommand:
            assert input_.data.sub_command is not None
            sub_command = input_.data.sub_command
            sub_aliases, sub_inputs = generate_sub_command_classes(module, symbols, sub_command, inputs_scope)
            aliases.update(sub_aliases)
            sub_command_type = _generate_sub_command(module, symbols, sub_command, sub_inputs, aliases)
            if sub_command_type is not None:
                aliases[sub_command.internal_id] = sub_command_type

        if input_.data.type.primitive == InputTypePrimitive.SubCommandUnion:
            assert input_.data.sub_command_union is not None
            for sub_command in input_.data.sub_command_union:
                sub_aliases, sub_inputs = generate_sub_command_classes(module, symbols, sub_command, inputs_scope)
                aliases.update(sub_aliases)
                sub_command_type = _generate_sub_command(module, symbols, sub_command, sub_inputs, aliases)
                if sub_command_type is not None:
                    aliases[sub_command.internal_id] = sub_command_type

    return aliases, inputs
