from styx.compiler.compile.common import SharedScopes, SharedSymbols
from styx.compiler.compile.inputs import codegen_var_is_set_by_user
from styx.model.core import InputArgument, InputTypePrimitive, OutputArgument, WithSymbol
from styx.pycodegen.core import PyFunc, PyModule, indent
from styx.pycodegen.utils import as_py_literal, enbrace, enquote


def _find_output_dependencies(
    output: WithSymbol[OutputArgument],
    inputs: list[WithSymbol[InputArgument]],
) -> list[WithSymbol[InputArgument]]:
    """Find the input dependencies for an output."""
    dependencies = []
    for input_ in inputs:
        if input_.data.template_key in output.data.path_template:
            dependencies.append(input_)
    return dependencies


def generate_outputs_definition(
    module: PyModule,
    symbols: SharedSymbols,
    outputs: list[WithSymbol[OutputArgument]],
    inputs: list[WithSymbol[InputArgument]],
) -> None:
    """Generate the static output class definition."""
    module.header.extend([
        "",
        "",
        f"class {symbols.output_class}(typing.NamedTuple):",
        *indent([
            '"""',
            f"Output object returned when calling `{symbols.function}(...)`.",
            '"""',
            "root: OutputPathType",
            '"""Output root folder. This is the root folder for all outputs."""',
        ]),
    ])
    for out in outputs:
        deps = _find_output_dependencies(out, inputs)
        if any([input_.data.type.is_optional for input_ in deps]):
            out_type = "OutputPathType | None"
        else:
            out_type = "OutputPathType"

        # Declaration
        module.header.extend(
            indent([
                f"{out.symbol}: {out_type}",
                f'"""{out.data.doc}"""',
            ])
        )


def generate_output_building(
    func: PyFunc,
    scopes: SharedScopes,
    symbols: SharedSymbols,
    outputs: list[WithSymbol[OutputArgument]],
    inputs: list[WithSymbol[InputArgument]],
) -> None:
    """Generate the output building code."""
    py_rstrip_fun = scopes.function.add_or_dodge("_rstrip")
    if any([out.data.stripped_file_extensions is not None for out in outputs]):
        func.body.extend([
            f"def {py_rstrip_fun}(s, r):",
            *indent([
                "for postfix in r:",
                *indent([
                    "if s.endswith(postfix):",
                    *indent(["return s[: -len(postfix)]"]),
                ]),
                "return s",
            ]),
        ])

    func.body.append(f"{symbols.ret} = {symbols.output_class}(")

    # Set root output path
    func.body.extend(indent([f'root={symbols.execution}.output_file("."),']))

    for out in outputs:
        strip_extensions = out.data.stripped_file_extensions is not None
        s_optional = ", optional=True" if out.data.optional else ""
        if out.data.path_template is not None:
            path_template = out.data.path_template

            input_dependencies = _find_output_dependencies(out, inputs)

            if len(input_dependencies) == 0:
                # No substitutions needed
                func.body.extend(
                    indent([f"{out.symbol}={symbols.execution}.output_file(f{enquote(path_template)}{s_optional}),"])
                )
            else:
                for input_ in input_dependencies:
                    substitute = input_.symbol

                    if input_.data.type.is_list:
                        raise Exception(f"Output path template replacements cannot be lists. ({input_.data.name})")

                    if input_.data.type.primitive == InputTypePrimitive.File:
                        # Just use the stem of the file
                        # This is commonly used when output files 'inherit' the name of an input file
                        substitute = f"pathlib.Path({substitute}).stem"
                    elif (input_.data.type.primitive == InputTypePrimitive.Number) or (
                        input_.data.type.primitive == InputTypePrimitive.Integer
                    ):
                        # Convert to string
                        substitute = f"str({substitute})"
                    elif input_.data.type.primitive != InputTypePrimitive.String:
                        raise Exception(
                            f"Unsupported input type {input_.data.type.primitive} "
                            f"for output path template of '{out.data.name}'."
                        )

                    if strip_extensions:
                        exts = as_py_literal(out.data.stripped_file_extensions, "'")
                        substitute = f"{py_rstrip_fun}({substitute}, {exts})"

                    path_template = path_template.replace(input_.data.template_key, enbrace(substitute))

                resolved_output = f"{symbols.execution}.output_file(f{enquote(path_template)}{s_optional})"

                if any([input_.data.type.is_optional for input_ in input_dependencies]):
                    # Codegen: Condition: Is any variable in the segment set by the user?
                    condition = [codegen_var_is_set_by_user(i) for i in input_dependencies]
                    resolved_output = f"{resolved_output} if {' and '.join(condition)} else None"

                func.body.extend(indent([f"{out.symbol}={resolved_output},"]))
        else:
            raise NotImplementedError

    func.body.extend([")"])
