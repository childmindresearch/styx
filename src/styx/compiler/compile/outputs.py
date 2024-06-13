from styx.compiler.compile.inputs import codegen_var_is_set_by_user
from styx.model.core import InputArgument, InputTypePrimitive, OutputArgument, SubCommand, WithSymbol
from styx.pycodegen.core import PyFunc, PyModule, indent
from styx.pycodegen.scope import Scope
from styx.pycodegen.utils import as_py_literal, enbrace, enquote


def _find_output_dependencies(
    output: WithSymbol[OutputArgument],
    inputs: list[WithSymbol[InputArgument]],
) -> list[WithSymbol[InputArgument]]:
    """Find the input dependencies for an output."""
    return [input_ for input_ in inputs if input_.data.template_key in output.data.path_template]


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


def generate_outputs_class(
    module: PyModule,
    symbol_output_class: str,
    symbol_parent_function: str,
    outputs: list[WithSymbol[OutputArgument]],
    inputs: list[WithSymbol[InputArgument]],
    sub_command_output_class_aliases: dict[str, str],
) -> None:
    """Generate the static output class definition."""
    module.header.extend([
        "",
        "",
        f"class {symbol_output_class}(typing.NamedTuple):",
        *indent([
            '"""',
            f"Output object returned when calling `{symbol_parent_function}(...)`.",
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

    for input_ in inputs:
        if input_.data.type.primitive == InputTypePrimitive.SubCommand:
            assert input_.data.sub_command is not None

            if _sub_command_has_outputs(input_.data.sub_command):
                sub_commands_type = sub_command_output_class_aliases[input_.data.sub_command.internal_id]
                if input_.data.type.is_list:
                    sub_commands_type = f"typing.List[{sub_commands_type}]"

                module.header.extend(
                    indent([
                        f"{input_.symbol}: {sub_commands_type}",
                        '"""Subcommand outputs"""',
                    ])
                )

        elif input_.data.type.primitive == InputTypePrimitive.SubCommandUnion:
            assert input_.data.sub_command_union is not None

            sub_commands = [
                sub_command_output_class_aliases[sub_command.internal_id]
                for sub_command in input_.data.sub_command_union
                if _sub_command_has_outputs(sub_command)
            ]
            if len(sub_commands) > 0:
                sub_commands_type = ", ".join(sub_commands)
                sub_commands_type = f"typing.Union[{sub_commands_type}]"

                if input_.data.type.is_list:
                    sub_commands_type = f"typing.List[{sub_commands_type}]"

                module.header.extend(
                    indent([
                        f"{input_.symbol}: {sub_commands_type}",
                        '"""Subcommand outputs"""',
                    ])
                )


def generate_output_building(
    func: PyFunc,
    func_scope: Scope,
    symbol_execution: str,
    symbol_output_class: str,
    symbol_return_var: str,
    outputs: list[WithSymbol[OutputArgument]],
    inputs: list[WithSymbol[InputArgument]],
    access_via_self: bool = False,
) -> None:
    """Generate the output building code."""
    py_rstrip_fun = func_scope.add_or_dodge("_rstrip")
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

    func.body.append(f"{symbol_return_var} = {symbol_output_class}(")

    # Set root output path
    func.body.extend(indent([f'root={symbol_execution}.output_file("."),']))

    for out in outputs:
        strip_extensions = out.data.stripped_file_extensions is not None
        s_optional = ", optional=True" if out.data.optional else ""
        if out.data.path_template is not None:
            path_template = out.data.path_template

            input_dependencies = _find_output_dependencies(out, inputs)

            if len(input_dependencies) == 0:
                # No substitutions needed
                func.body.extend(
                    indent([f"{out.symbol}={symbol_execution}.output_file(f{enquote(path_template)}{s_optional}),"])
                )
            else:
                for input_ in input_dependencies:
                    substitute = input_.symbol

                    if access_via_self:
                        substitute = f"self.{substitute}"

                    if input_.data.type.is_list:
                        raise Exception(f"Output path template replacements cannot be lists. ({input_.data.name})")

                    if input_.data.type.primitive == InputTypePrimitive.File:
                        # Just use the name of the file
                        # This is commonly used when output files 'inherit' the name of an input file
                        substitute = f"pathlib.Path({substitute}).name"
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

                resolved_output = f"{symbol_execution}.output_file(f{enquote(path_template)}{s_optional})"

                if any([input_.data.type.is_optional for input_ in input_dependencies]):
                    # Codegen: Condition: Is any variable in the segment set by the user?
                    condition = [codegen_var_is_set_by_user(i) for i in input_dependencies]
                    resolved_output = f"{resolved_output} if {' and '.join(condition)} else None"

                func.body.extend(indent([f"{out.symbol}={resolved_output},"]))
        else:
            raise NotImplementedError

    for input_ in inputs:
        if (input_.data.type.primitive == InputTypePrimitive.SubCommand) or (
            input_.data.type.primitive == InputTypePrimitive.SubCommandUnion
        ):
            if input_.data.type.primitive == InputTypePrimitive.SubCommand:
                assert input_.data.sub_command is not None
                has_outouts = _sub_command_has_outputs(input_.data.sub_command)
            else:
                assert input_.data.sub_command_union is not None
                has_outouts = any([
                    _sub_command_has_outputs(sub_command) for sub_command in input_.data.sub_command_union
                ])
            if has_outouts:
                resolved_input = input_.symbol
                if access_via_self:
                    resolved_input = f"self.{resolved_input}"

                if input_.data.type.is_list:
                    func.body.extend(
                        indent([f"{input_.symbol}=" f"[i.outputs({symbol_execution}) for i in {resolved_input}],"])
                    )
                else:
                    func.body.extend(indent([f"{input_.symbol}={resolved_input}.outputs({symbol_execution}),"]))

    func.body.extend([")"])
