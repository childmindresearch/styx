from styx.compiler.compile.common import SharedScopes, SharedSymbols
from styx.model.core import InputArgument, OutputArgument, WithSymbol
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

    for out in outputs:
        strip_extensions = out.data.stripped_file_extensions is not None
        if out.data.path_template is not None:
            s = out.data.path_template
            for a in inputs:
                if strip_extensions:
                    exts = as_py_literal(out.data.stripped_file_extensions, "'")
                    s = s.replace(f"{a.data.internal_id}", enbrace(f"{py_rstrip_fun}({a.symbol}, {exts})"))
                else:
                    s = s.replace(f"{a.data.internal_id}", enbrace(a.symbol))

            s_optional = ", optional=True" if out.data.optional else ""

            func.body.extend(indent([f"{out.symbol}={symbols.execution}.output_file(f{enquote(s)}{s_optional}),"]))
        else:
            raise NotImplementedError

    func.body.extend([")"])
