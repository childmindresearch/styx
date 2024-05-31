from styx.compiler.compile.common import SharedSymbols
from styx.compiler.compile.constraints import generate_constraint_checks
from styx.compiler.compile.inputs import build_input_arguments, generate_command_line_args_building
from styx.compiler.compile.outputs import generate_output_building, generate_outputs_class
from styx.model.core import InputArgument, InputTypePrimitive, OutputArgument, SubCommand, WithSymbol
from styx.pycodegen.core import PyArg, PyDataClass, PyFunc, PyModule, blank_before
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import python_pascalize, python_snakify


def _sub_command_class_name(symbol_module: str, sub_command: SubCommand) -> str:
    """Return the name of the sub-command class."""
    # Prefix the sub-command name with the module name so its likely unique across modules.
    return python_pascalize(f"{symbol_module}_{sub_command.name}")


def _sub_command_output_class_name(symbol_module: str, sub_command: SubCommand) -> str:
    """Return the name of the sub-command output class."""
    # Prefix the sub-command name with the module name so its likely unique across modules.
    return python_pascalize(f"{symbol_module}_{sub_command.name}_Outputs")


def _sub_command_has_outputs(sub_command: SubCommand) -> bool:
    """Check if the sub-command has outputs."""
    if len(sub_command.outputs) > 0:
        return True
    for input_ in sub_command.inputs:
        if input_.type.primitive == InputTypePrimitive.SubCommand:
            assert input_.sub_command is not None
            if _sub_command_has_outputs(input_.sub_command):
                return True
        if input_.type.primitive == InputTypePrimitive.SubCommandUnion:
            assert input_.sub_command_union is not None
            for sub_command in input_.sub_command_union:
                if _sub_command_has_outputs(sub_command):
                    return True
    return False


def _generate_sub_command(
    module: PyModule,
    scope_module: Scope,
    symbols: SharedSymbols,
    sub_command: SubCommand,
    outputs: list[WithSymbol[OutputArgument]],
    inputs: list[WithSymbol[InputArgument]],
    aliases: dict[str, str],
    sub_command_output_class_aliases: dict[str, str],
) -> tuple[str, str]:
    """Generate the static output class definition."""
    class_name = scope_module.add_or_dodge(_sub_command_class_name(symbols.function, sub_command))
    output_class_name = scope_module.add_or_dodge(_sub_command_output_class_name(symbols.function, sub_command))

    module.exports.append(class_name)
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
            PyArg(name="execution", type="Execution", default=None, docstring="The execution object."),
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

    # Outputs method

    outputs_method = PyFunc(
        name="outputs",
        docstring_body="Collect output file paths.",
        return_type=output_class_name,
        return_descr=f"NamedTuple of outputs (described in `{output_class_name}`).",
        args=[
            PyArg(name="self", type=None, default=None, docstring="The sub-command object."),
            PyArg(name="execution", type="Execution", default=None, docstring="The execution object."),
        ],
        body=[],
    )

    if _sub_command_has_outputs(sub_command):
        generate_outputs_class(
            module,
            output_class_name,
            class_name + ".run",
            outputs,
            inputs_self,
            sub_command_output_class_aliases,
        )
        module.exports.append(output_class_name)
        generate_output_building(
            outputs_method, Scope(), symbols.execution, output_class_name, "ret", outputs, inputs_self
        )
        outputs_method.body.extend(["return ret"])
        sub_command_class.methods.append(outputs_method)

    module.header.extend(blank_before(sub_command_class.generate(), 2))
    if "import dataclasses" not in module.imports:
        module.imports.append("import dataclasses")

    return class_name, output_class_name


def generate_sub_command_classes(
    module: PyModule,
    symbols: SharedSymbols,
    command: SubCommand,
    scope_module: Scope,
) -> tuple[dict[str, str], dict[str, str], list[WithSymbol[InputArgument]]]:
    """Build Python function arguments from input arguments."""
    # internal_id -> class_name
    aliases: dict[str, str] = {}
    # subcommand.internal_id -> subcommand.outputs() class name
    sub_command_output_class_aliases: dict[str, str] = {}

    inputs_scope = Scope(parent=scope_module)
    outputs_scope = Scope(parent=scope_module)

    # Input symbols
    inputs: list[WithSymbol[InputArgument]] = []
    for i in command.inputs:
        py_symbol = inputs_scope.add_or_dodge(python_snakify(i.name))
        inputs.append(WithSymbol(i, py_symbol))

    for input_ in inputs:
        if input_.data.type.primitive == InputTypePrimitive.SubCommand:
            assert input_.data.sub_command is not None
            sub_command = input_.data.sub_command
            sub_aliases, sub_sub_command_output_class_aliases, sub_inputs = generate_sub_command_classes(
                module, symbols, sub_command, inputs_scope
            )
            aliases.update(sub_aliases)
            sub_command_output_class_aliases.update(sub_sub_command_output_class_aliases)

            sub_outputs = []
            for output in sub_command.outputs:
                py_symbol = outputs_scope.add_or_dodge(python_snakify(output.name))
                sub_outputs.append(WithSymbol(output, py_symbol))

            sub_command_type, sub_command_output_type = _generate_sub_command(
                module,
                scope_module,
                symbols,
                sub_command,
                sub_outputs,
                sub_inputs,
                aliases,
                sub_command_output_class_aliases,
            )
            aliases[sub_command.internal_id] = sub_command_type
            sub_command_output_class_aliases[sub_command.internal_id] = sub_command_output_type

        if input_.data.type.primitive == InputTypePrimitive.SubCommandUnion:
            assert input_.data.sub_command_union is not None
            for sub_command in input_.data.sub_command_union:
                sub_aliases, sub_sub_command_output_class_aliases, sub_inputs = generate_sub_command_classes(
                    module, symbols, sub_command, inputs_scope
                )
                aliases.update(sub_aliases)
                sub_command_output_class_aliases.update(sub_sub_command_output_class_aliases)

                sub_outputs = []
                for output in sub_command.outputs:
                    py_symbol = outputs_scope.add_or_dodge(python_snakify(output.name))
                    sub_outputs.append(WithSymbol(output, py_symbol))

                sub_command_type, sub_command_output_type = _generate_sub_command(
                    module,
                    scope_module,
                    symbols,
                    sub_command,
                    sub_outputs,
                    sub_inputs,
                    aliases,
                    sub_command_output_class_aliases,
                )
                aliases[sub_command.internal_id] = sub_command_type
                sub_command_output_class_aliases[sub_command.internal_id] = sub_command_output_type

    return aliases, sub_command_output_class_aliases, inputs
