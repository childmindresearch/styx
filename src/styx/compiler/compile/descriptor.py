from styx.compiler.compile.common import SharedScopes, SharedSymbols
from styx.compiler.compile.constraints import generate_constraint_checks
from styx.compiler.compile.inputs import build_input_arguments, generate_command_line_args_building
from styx.compiler.compile.metadata import generate_static_metadata
from styx.compiler.compile.outputs import generate_output_building, generate_outputs_class
from styx.compiler.compile.subcommand import generate_sub_command_classes
from styx.compiler.settings import CompilerSettings
from styx.model.core import Descriptor, InputArgument, OutputArgument, SubCommand, WithSymbol
from styx.pycodegen.core import PyArg, PyFunc, PyModule
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import (
    python_pascalize,
    python_screaming_snakify,
    python_snakify,
)


def _generate_run_function(
    module: PyModule,
    symbols: SharedSymbols,
    scopes: SharedScopes,
    command: SubCommand,
    inputs: list[WithSymbol[InputArgument]],
    outputs: list[WithSymbol[OutputArgument]],
) -> None:
    # Sub-command classes
    sub_aliases, sub_sub_command_class_aliases, _ = generate_sub_command_classes(
        module, symbols, command, scopes.module
    )

    # Function
    func = PyFunc(
        name=symbols.function,
        return_type=symbols.output_class,
        return_descr=f"NamedTuple of outputs " f"(described in `{symbols.output_class}`).",
        docstring_body=command.doc,
    )
    module.funcs.append(func)

    # Function arguments
    func.args.extend(build_input_arguments(inputs, sub_aliases))
    func.args.append(PyArg(name="runner", type="Runner | None", default="None", docstring="Command runner"))

    # Function body: Runner instantiation
    func.body.extend([
        f"{symbols.runner} = {symbols.runner} or get_global_runner()",
    ])

    # Constraint checking
    generate_constraint_checks(func, command.group_constraints, inputs)

    # Function body
    func.body.extend([
        f"{symbols.execution} = {symbols.runner}.start_execution({symbols.metadata})",
        f"{symbols.cargs} = []",
    ])

    # Command line args building
    generate_command_line_args_building(command.input_command_line_template, func, inputs)

    # Outputs static definition
    generate_outputs_class(
        module, symbols.output_class, symbols.function, outputs, inputs, sub_sub_command_class_aliases
    )
    # Outputs building code
    generate_output_building(
        func, scopes.function, symbols.execution, symbols.output_class, symbols.ret, outputs, inputs, False
    )

    # Function body: Run and return
    func.body.extend([
        f"{symbols.execution}.run({symbols.cargs})",
        f"return {symbols.ret}",
    ])


def compile_descriptor(descriptor: Descriptor, settings: CompilerSettings) -> str:
    """Compile a descriptor to Python code."""
    # --- Scopes and symbols ---

    _module_scope = Scope(parent=Scope.python())
    scopes = SharedScopes(
        module=_module_scope,
        function=Scope(parent=_module_scope),
        output_tuple=Scope(parent=_module_scope),
    )

    # Module level symbols
    scopes.module.add_or_die("styx")
    scopes.module.add_or_die("InputFileType")
    scopes.module.add_or_die("OutputFileType")
    scopes.module.add_or_die("Runner")
    scopes.module.add_or_die("Execution")
    scopes.module.add_or_die("Metadata")

    symbols = SharedSymbols(
        function=scopes.module.add_or_dodge(python_snakify(descriptor.command.name)),
        output_class=scopes.module.add_or_dodge(f"{python_pascalize(descriptor.command.name)}Outputs"),
        metadata=scopes.module.add_or_dodge(f"{python_screaming_snakify(descriptor.command.name)}_METADATA"),
        runner=scopes.function.add_or_die("runner"),
        execution=scopes.function.add_or_die("execution"),
        cargs=scopes.function.add_or_die("cargs"),
        ret=scopes.function.add_or_die("ret"),
    )

    # Input symbols
    inputs: list[WithSymbol[InputArgument]] = []
    for input_ in descriptor.command.inputs:
        py_symbol = scopes.function.add_or_dodge(python_snakify(input_.name))
        inputs.append(WithSymbol(input_, py_symbol))

    # Output symbols
    outputs: list[WithSymbol[OutputArgument]] = []
    for output in descriptor.command.outputs:
        py_symbol = scopes.output_tuple.add_or_dodge(python_snakify(output.name))
        outputs.append(WithSymbol(output, py_symbol))

    # --- Code generation ---
    module = PyModule()

    module.imports.append("import typing")
    module.imports.append("import pathlib")
    module.imports.append("from styxdefs import *")

    module.exports.append(symbols.function)
    module.exports.append(symbols.output_class)
    module.exports.append(symbols.metadata)

    # Static metadata
    generate_static_metadata(module, descriptor, symbols)

    # Main command run function
    _generate_run_function(
        module,
        symbols,
        scopes,
        command=descriptor.command,
        inputs=inputs,
        outputs=outputs,
    )

    # --- Return code ---

    module.imports.sort()
    module.exports.sort()
    return module.text()
