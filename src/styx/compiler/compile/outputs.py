from styx.model.core import InputArgument, OutputArgument, WithSymbol
from styx.pycodegen.core import LineBuffer, indent
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import as_py_literal, enbrace, enquote


def compile_output_file_expr(
    func_scope: Scope,
    buf_header: LineBuffer,
    buf_body: LineBuffer,
    outputs: list[WithSymbol[OutputArgument]],
    inputs: list[WithSymbol[InputArgument]],
    py_var_output_class: str,
    py_var_execution: str,
    py_var_ret: str,
) -> None:
    py_rstrip_fun = func_scope.add_or_dodge("_rstrip")
    if any([out.data.stripped_file_extensions is not None for out in outputs]):
        buf_body.extend([
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

    buf_body.append(f"{py_var_ret} = {py_var_output_class}(")

    for out in outputs:
        # Declaration
        buf_header.extend(
            indent([
                f"{out.symbol}: R",
                f'"""{out.data.description}"""',
            ])
        )

        strip_extensions = out.data.stripped_file_extensions is not None

        # Expression
        if out.data.path_template is not None:
            s = out.data.path_template
            for a in inputs:
                if strip_extensions:
                    exts = as_py_literal(out.data.stripped_file_extensions, "'")
                    s = s.replace(f"{a.data.bt_ref}", enbrace(f"{py_rstrip_fun}({a.symbol}, {exts})"))
                else:
                    s = s.replace(f"{a.data.bt_ref}", enbrace(a.symbol))

            s_optional = ", optional=True" if out.data.optional else ""

            buf_body.extend(indent([f"{out.symbol}={py_var_execution}.output_file(f{enquote(s)}{s_optional}),"]))
        else:
            raise NotImplementedError

    buf_body.extend([")"])
