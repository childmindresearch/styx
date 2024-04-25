from styx.compiler.compile.common import SharedScopes, SharedSymbols
from styx.compiler.compile.constraints import generate_constraint_checks
from styx.compiler.compile.definitions import compile_definitions, generate_definitions
from styx.compiler.compile.inputs import build_input_arguments, generate_command_line_args_building
from styx.compiler.compile.metadata import generate_static_metadata
from styx.compiler.compile.outputs import generate_output_building, generate_outputs_definition
from styx.compiler.settings import CompilerSettings, DefsMode
from styx.model.core import Descriptor, InputArgument, OutputArgument, WithSymbol
from styx.pycodegen.core import PyArg, PyFunc, PyModule
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import (
    python_pascalize,
    python_screaming_snakify,
    python_snakify,
)


def compile_descriptor(descriptor: Descriptor, settings: CompilerSettings) -> str:
    """Compile a descriptor to Python code."""
    if settings.defs_mode == DefsMode.DEFS_ONLY:
        return compile_definitions()

    # --- Scopes and symbols ---

    _module_scope = Scope(parent=Scope.python())
    scopes = SharedScopes(
        module=_module_scope,
        function=Scope(parent=_module_scope),
        output_tuple=Scope(parent=_module_scope),
    )

    # Module level symbols
    scopes.module.add_or_die("styx")
    scopes.module.add_or_die("P")
    scopes.module.add_or_die("R")
    scopes.module.add_or_die("Runner")
    scopes.module.add_or_die("Execution")
    scopes.module.add_or_die("Metadata")

    symbols = SharedSymbols(
        function=scopes.module.add_or_dodge(python_snakify(descriptor.name)),
        output_class=scopes.module.add_or_dodge(f"{python_pascalize(descriptor.name)}Outputs"),
        metadata=scopes.module.add_or_dodge(f"{python_screaming_snakify(descriptor.name)}_METADATA"),
        runner=scopes.function.add_or_die("runner"),
        execution=scopes.function.add_or_die("execution"),
        cargs=scopes.function.add_or_die("cargs"),
        ret=scopes.function.add_or_die("ret"),
    )

    # Input symbols
    inputs: list[WithSymbol[InputArgument]] = []
    inputs_lookup_bt_name: dict[str, WithSymbol[InputArgument]] = {}
    for input_ in descriptor.inputs:
        py_symbol = scopes.function.add_or_dodge(python_snakify(input_.name))
        input_with_symbol = WithSymbol(input_, py_symbol)
        inputs.append(input_with_symbol)
        inputs_lookup_bt_name[input_.name] = input_with_symbol

    # Output symbols
    outputs: list[WithSymbol[OutputArgument]] = []
    for output in descriptor.outputs:
        py_symbol = scopes.output_tuple.add_or_dodge(python_snakify(output.name))
        outputs.append(WithSymbol(output, py_symbol))

    # --- Code generation ---

    module = PyModule()
    module.imports.extend(["import typing"])
    func = PyFunc(
        name=symbols.function,
        return_type=f"{symbols.output_class}[R]",
        return_descr=f"NamedTuple of outputs " f"(described in `{symbols.output_class}`).",
        docstring_body=descriptor.description,
    )
    module.funcs.append(func)

    # Function arguments
    func.args.append(PyArg(name="runner", type="Runner[P, R]", default=None, docstring="Command runner"))
    func.args.extend(build_input_arguments(inputs))

    # Constraint checking
    generate_constraint_checks(func, descriptor, inputs, inputs_lookup_bt_name)

    # Function body
    func.body.extend([
        f"{symbols.execution} = {symbols.runner}.start_execution({symbols.metadata})",
        f"{symbols.cargs} = []",
    ])

    # Command line args building
    generate_command_line_args_building(descriptor, symbols, func, inputs)

    # Definitions
    generate_definitions(module, settings)
    module.header.extend(["", ""])  # Two blank lines

    # Static metadata
    generate_static_metadata(module, descriptor, symbols)

    # Outputs static definition
    generate_outputs_definition(module, symbols, outputs)
    # Outputs building code
    generate_output_building(func, scopes, symbols, outputs, inputs)

    # Function body: Run and return
    func.body.extend([
        f"{symbols.execution}.run({symbols.cargs})",
        f"return {symbols.ret}",
    ])

    # --- Return code ---

    module.imports.sort()
    return module.text()
