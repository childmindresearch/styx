from styx.compiler.compile.common import SharedScopes, SharedSymbols
from styx.model.core import InputArgument, InputTypePrimitive, OutputArgument, WithSymbol
from styx.pycodegen.core import PyFunc, PyModule, indent
from styx.pycodegen.utils import as_py_literal, enbrace, enquote


def generate_outputs_definition(
    module: PyModule,
    symbols: SharedSymbols,
    outputs: list[WithSymbol[OutputArgument]],
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
        # Declaration
        module.header.extend(
            indent([
                f"{out.symbol}: OutputPathType",
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
        if out.data.path_template is not None:
            s = out.data.path_template
            for input_ in inputs:
                if input_.data.template_key not in s:
                    continue

                substitute = input_.symbol

                if input_.data.type.primitive == InputTypePrimitive.File:
                    # Just use the stem of the file
                    # This is commonly used when output files 'inherit' the name of an input file
                    substitute = f"pathlib.Path({substitute}).stem"
                elif input_.data.type.primitive != InputTypePrimitive.String:
                    raise Exception(
                        f"Unsupported input type {input_.data.type.primitive} "
                        f"for output path template of '{out.data.name}'."
                    )

                if strip_extensions:
                    exts = as_py_literal(out.data.stripped_file_extensions, "'")
                    substitute = f"{py_rstrip_fun}({substitute}, {exts})"

                s = s.replace(input_.data.template_key, enbrace(substitute))

            s_optional = ", optional=True" if out.data.optional else ""

            func.body.extend(indent([f"{out.symbol}={symbols.execution}.output_file(f{enquote(s)}{s_optional}),"]))
        else:
            raise NotImplementedError

    func.body.extend([")"])
