import styx.ir.core as ir
from styx.backend.generic.documentation import docs_to_docstring
from styx.backend.generic.gen.constraints import struct_compile_constraint_checks
from styx.backend.generic.gen.lookup import LookupParam
from styx.backend.generic.gen.metadata import generate_static_metadata
from styx.backend.generic.languageprovider import LanguageProvider
from styx.backend.generic.linebuffer import LineBuffer
from styx.backend.generic.model import GenericArg, GenericDataClass, GenericFunc, GenericModule, GenericNamedTuple
from styx.backend.generic.scope import Scope
from styx.backend.generic.utils import enquote, struct_has_outputs


def _compile_struct(
    lang: LanguageProvider,
    struct: ir.Param[ir.Param.Struct],
    interface_module: GenericModule,
    lookup: LookupParam,
    metadata_symbol: str,
    root_function: bool,
    stdout_as_string_output: ir.StdOutErrAsStringOutput | None = None,
    stderr_as_string_output: ir.StdOutErrAsStringOutput | None = None,
) -> None:
    has_outputs = root_function or struct_has_outputs(struct)

    outputs_type = lookup.py_output_type[struct.base.id_]

    func_cargs_building: GenericFunc
    if root_function:
        func_cargs_building = GenericFunc(
            name=lookup.py_type[struct.base.id_],
            return_type=outputs_type,
            return_descr=f"NamedTuple of outputs (described in `{outputs_type}`).",
            docstring_body=docs_to_docstring(struct.base.docs),
        )
        pyargs = func_cargs_building.args
    else:
        func_cargs_building = GenericFunc(
            name="run",
            docstring_body="Build command line arguments. This method is called by the main command.",
            return_type=lang.type_string_list(),
            return_descr="Command line arguments",
            args=[
                GenericArg(name="self", type=None, default=None, docstring="The sub-command object."),
                GenericArg(
                    name="execution", type=lang.execution_type(), default=None, docstring="The execution object."
                ),
            ],
        )
        struct_class: GenericDataClass = GenericDataClass(
            name=lookup.py_struct_type[struct.base.id_],
            docstring=docs_to_docstring(struct.base.docs),
            methods=[func_cargs_building],
        )
        if has_outputs:
            func_outputs = GenericFunc(
                name="outputs",
                docstring_body="Collect output file paths.",
                return_type=outputs_type,
                return_descr=f"NamedTuple of outputs (described in `{outputs_type}`).",
                args=[
                    GenericArg(name="self", type=None, default=None, docstring="The sub-command object."),
                    GenericArg(
                        name="execution", type=lang.execution_type(), default=None, docstring="The execution object."
                    ),
                ],
            )
        pyargs = struct_class.fields

    # Collect param python symbols
    for elem in struct.body.iter_params():
        symbol = lookup.py_symbol[elem.base.id_]
        pyargs.append(
            GenericArg(
                name=symbol,
                type=lookup.py_type[elem.base.id_],
                default=lang.param_default_value(elem),
                docstring=elem.base.docs.description,
            )
        )

        if isinstance(elem.body, ir.Param.Struct):
            _compile_struct(
                lang=lang,
                struct=elem,
                interface_module=interface_module,
                lookup=lookup,
                metadata_symbol=metadata_symbol,
                root_function=False,
            )
        elif isinstance(elem.body, ir.Param.StructUnion):
            for child in elem.body.alts:
                _compile_struct(
                    lang=lang,
                    struct=child,
                    interface_module=interface_module,
                    lookup=lookup,
                    metadata_symbol=metadata_symbol,
                    root_function=False,
                )

    struct_compile_constraint_checks(lang=lang, func=func_cargs_building, struct=struct, lookup=lookup)

    if has_outputs:
        _compile_outputs_class(
            lang=lang,
            struct=struct,
            interface_module=interface_module,
            lookup=lookup,
            stdout_as_string_output=stdout_as_string_output,
            stderr_as_string_output=stderr_as_string_output,
        )

    if root_function:
        func_cargs_building.body.extend([
            *lang.runner_declare("runner"),
            *lang.execution_declare("execution", metadata_symbol),
        ])

    _compile_cargs_building(lang, struct, lookup, func_cargs_building, access_via_self=not root_function)

    if root_function:
        pyargs.append(
            GenericArg(
                name="runner",
                type=lang.type_symbol_as_optional(lang.runner_type()),
                default=lang.null(),
                docstring="Command runner",
            )
        )
        _compile_outputs_building(
            lang=lang,
            struct=struct,
            func=func_cargs_building,
            lookup=lookup,
            access_via_self=False,
            stderr_as_string_output=stderr_as_string_output,
            stdout_as_string_output=stdout_as_string_output,
        )
        func_cargs_building.body.extend([
            *lang.execution_run(
                execution_symbol="execution",
                cargs_symbol="cargs",
                stdout_output_symbol=lookup.py_output_field_symbol[stdout_as_string_output.id_]
                if stdout_as_string_output
                else None,
                stderr_output_symbol=lookup.py_output_field_symbol[stderr_as_string_output.id_]
                if stderr_as_string_output
                else None,
            ),
            lang.return_statement("ret"),
        ])
        interface_module.funcs_and_classes.append(func_cargs_building)
    else:
        if has_outputs:
            _compile_outputs_building(
                lang=lang,
                struct=struct,
                func=func_outputs,
                lookup=lookup,
                access_via_self=True,
            )
            func_outputs.body.extend([lang.return_statement("ret")])
            struct_class.methods.append(func_outputs)
        func_cargs_building.body.extend([lang.return_statement("cargs")])
        interface_module.funcs_and_classes.append(struct_class)
        interface_module.exports.append(struct_class.name)


def _compile_cargs_building(
    lang: LanguageProvider,
    param: ir.Param[ir.Param.Struct],
    lookup: LookupParam,
    func: GenericFunc,
    access_via_self: bool,
) -> None:
    func.body.extend(lang.cargs_declare("cargs"))

    for group in param.body.groups:
        group_conditions_py = []

        building_cargs_py: list[tuple[str, bool]] = []
        building_cargs_py_maybe_null: list[tuple[str, bool]] = []
        for carg in group.cargs:
            building_carg_py: list[tuple[str, bool]] = []
            building_carg_py_maybe_null: list[tuple[str, bool]] = []
            for token in carg.tokens:
                if isinstance(token, str):
                    building_carg_py.append((lang.as_literal(token), False))
                    building_carg_py_maybe_null.append((lang.as_literal(token), False))
                    continue
                elem_symbol = lookup.py_symbol[token.base.id_]
                if access_via_self:
                    elem_symbol = lang.member_access(elem_symbol)
                py_var_as_str, py_var_as_str_is_array = lang.param_var_to_str(token, elem_symbol)
                building_carg_py.append((py_var_as_str, py_var_as_str_is_array))
                if (py_var_is_set_by_user := lang.param_var_is_set_by_user(token, elem_symbol, False)) is not None:
                    group_conditions_py.append(py_var_is_set_by_user)
                    building_carg_py_maybe_null.append(
                        (
                            lang.ternary(py_var_is_set_by_user, py_var_as_str, lang.empty_str_list(), True),
                            py_var_as_str_is_array,
                        )
                        if py_var_as_str_is_array
                        else (
                            lang.ternary(py_var_is_set_by_user, py_var_as_str, lang.empty_str(), True),
                            py_var_as_str_is_array,
                        )
                    )
                else:
                    building_carg_py_maybe_null.append((py_var_as_str, py_var_as_str_is_array))

            if len(building_carg_py) == 1:
                building_cargs_py.append(building_carg_py[0])
                building_cargs_py_maybe_null.append(building_carg_py_maybe_null[0])
            else:
                destructured = [
                    s if not s_is_list else lang.join_string_list_expr(s) for s, s_is_list in building_carg_py
                ]
                building_cargs_py.append((lang.concat_strings(destructured), False))
                destructured = [
                    s if not s_is_list else lang.join_string_list_expr(s)
                    for s, s_is_list in building_carg_py_maybe_null
                ]
                building_cargs_py_maybe_null.append((lang.concat_strings(destructured), False))

        buf_appending: LineBuffer = []

        if len(building_cargs_py) == 1:
            for val, val_is_list in building_cargs_py_maybe_null if len(group_conditions_py) > 1 else building_cargs_py:
                if val_is_list:
                    buf_appending.extend(lang.cargs_add_1d("cargs", val))
                else:
                    buf_appending.extend(lang.cargs_add_0d("cargs", val))
        else:
            x = lang.cargs_0d_or_1d_to_0d(
                building_cargs_py_maybe_null if len(group_conditions_py) > 1 else building_cargs_py
            )
            buf_appending.extend(lang.cargs_add_0d("cargs", x))

        if len(group_conditions_py) > 0:
            func.body.extend(
                lang.if_else_block(
                    condition=lang.conditions_join_or(group_conditions_py),
                    truthy=buf_appending,
                )
            )
        else:
            func.body.extend(buf_appending)


def _compile_outputs_class(
    lang: LanguageProvider,
    struct: ir.Param[ir.Param.Struct],
    interface_module: GenericModule,
    lookup: LookupParam,
    stdout_as_string_output: ir.StdOutErrAsStringOutput | None = None,
    stderr_as_string_output: ir.StdOutErrAsStringOutput | None = None,
) -> None:
    outputs_class: GenericNamedTuple = GenericNamedTuple(
        name=lookup.py_output_type[struct.base.id_],
        docstring=f"Output object returned when calling `{lookup.py_type[struct.base.id_]}(...)`.",
    )
    outputs_class.fields.append(
        GenericArg(
            name="root",
            type="OutputPathType",
            default=None,
            docstring="Output root folder. This is the root folder for all outputs.",
        )
    )

    for stdout_stderr_output in (stdout_as_string_output, stderr_as_string_output):
        if stdout_stderr_output is None:
            continue
        outputs_class.fields.append(
            GenericArg(
                name=lookup.py_output_field_symbol[stdout_stderr_output.id_],
                type=lang.type_string_list(),
                default=None,
                docstring=stdout_stderr_output.docs.description,
            )
        )

    for output in struct.base.outputs:
        output_symbol = lookup.py_output_field_symbol[output.id_]

        # Optional if any of its param references is optional
        optional = False
        for token in output.tokens:
            if isinstance(token, str):
                continue
            optional = optional or lookup.param[token.ref_id].nullable

        output_type = lang.output_path_type()
        if optional:
            output_type = lang.type_symbol_as_optional(output_type)

        outputs_class.fields.append(
            GenericArg(
                name=output_symbol,
                type=output_type,
                default=None,
                docstring=output.docs.description,
            )
        )

    for sub_struct in struct.body.iter_params():
        if isinstance(sub_struct.body, ir.Param.Struct):
            if struct_has_outputs(sub_struct):
                output_type = lookup.py_output_type[sub_struct.base.id_]
                if sub_struct.list_:
                    output_type = lang.type_symbol_as_list(output_type)
                if sub_struct.nullable:
                    output_type = lang.type_symbol_as_optional(output_type)

                output_symbol = lookup.py_output_field_symbol[sub_struct.base.id_]

                input_type = lookup.py_struct_type[sub_struct.base.id_]
                docs_append = ""
                if sub_struct.list_:
                    docs_append = "This is a list of outputs with the same length and order as the inputs."

                outputs_class.fields.append(
                    GenericArg(
                        name=output_symbol,
                        type=output_type,
                        default=None,
                        docstring=f"Outputs from {enquote(input_type, '`')}.{docs_append}",
                    )
                )
        elif isinstance(sub_struct.body, ir.Param.StructUnion):
            if any([struct_has_outputs(s) for s in sub_struct.body.alts]):
                alt_types = [
                    lookup.py_output_type[sub_command.base.id_]
                    for sub_command in sub_struct.body.alts
                    if struct_has_outputs(sub_command)
                ]
                if len(alt_types) > 0:
                    output_type = lang.type_symbols_as_union(alt_types)

                    if sub_struct.list_:
                        output_type = lang.type_symbol_as_list(output_type)
                    if sub_struct.nullable:
                        output_type = lang.type_symbol_as_optional(output_type)

                    output_symbol = lookup.py_output_field_symbol[sub_struct.base.id_]

                    alt_input_types = [
                        lookup.py_struct_type[sub_command.base.id_]
                        for sub_command in sub_struct.body.alts
                        if struct_has_outputs(sub_command)
                    ]
                    docs_append = ""
                    if sub_struct.list_:
                        docs_append = "This is a list of outputs with the same length and order as the inputs."

                    input_types_human = " or ".join([enquote(t, "`") for t in alt_input_types])
                    outputs_class.fields.append(
                        GenericArg(
                            name=output_symbol,
                            type=output_type,
                            default=None,
                            docstring=f"Outputs from {input_types_human}.{docs_append}",
                        )
                    )

    interface_module.funcs_and_classes.append(outputs_class)
    interface_module.exports.append(outputs_class.name)


def _compile_outputs_building(
    lang: LanguageProvider,
    struct: ir.Param[ir.Param.Struct],
    func: GenericFunc,
    lookup: LookupParam,
    access_via_self: bool = False,
    stdout_as_string_output: ir.StdOutErrAsStringOutput | None = None,
    stderr_as_string_output: ir.StdOutErrAsStringOutput | None = None,
) -> None:
    """Generate the outputs building code."""
    members = {}

    def _py_get_val(
        output_param_reference: ir.OutputParamReference,
    ) -> str:
        param = lookup.param[output_param_reference.ref_id]
        symbol = lookup.py_symbol[param.base.id_]

        substitute = symbol
        if access_via_self:
            substitute = lang.member_access(substitute)

        if param.list_:
            raise Exception(f"Output path template replacements cannot be lists. ({param.base.name})")

        if isinstance(param.body, ir.Param.String):
            return lang.remove_suffixes(substitute, output_param_reference.file_remove_suffixes)

        if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
            return lang.numeric_to_str(substitute)

        if isinstance(param.body, ir.Param.File):
            return lang.remove_suffixes(
                lang.path_expr_get_filename(substitute), output_param_reference.file_remove_suffixes
            )

        if isinstance(param.body, ir.Param.Bool):
            raise Exception(f"Unsupported input type for output path template of '{param.base.name}'.")
        assert False

    for stdout_stderr_output in (stdout_as_string_output, stderr_as_string_output):
        if stdout_stderr_output is None:
            continue
        output_symbol = lookup.py_output_field_symbol[stdout_stderr_output.id_]

        members[output_symbol] = lang.empty_str_list()

    for output in struct.base.outputs:
        output_symbol = lookup.py_output_field_symbol[output.id_]

        output_segments: list[str] = []
        conditions = []
        for token in output.tokens:
            if isinstance(token, str):
                output_segments.append(lang.as_literal(token))
                continue
            output_segments.append(_py_get_val(token))

            ostruct = lookup.param[token.ref_id]
            param_symbol = lookup.py_symbol[ostruct.base.id_]
            if (py_var_is_set_by_user := lang.param_var_is_set_by_user(ostruct, param_symbol, False)) is not None:
                conditions.append(py_var_is_set_by_user)

        if len(conditions) > 0:
            members[output_symbol] = lang.ternary(
                condition=lang.conditions_join_and(conditions),
                truthy=lang.resolve_output_file("execution", lang.concat_strings(output_segments)),
                falsy=lang.null(),
            )
        else:
            members[output_symbol] = lang.resolve_output_file("execution", lang.concat_strings(output_segments))

    # sub struct outputs
    for sub_struct in struct.body.iter_params():
        has_outputs = False
        if isinstance(sub_struct.body, ir.Param.Struct):
            has_outputs = struct_has_outputs(sub_struct)
        elif isinstance(sub_struct.body, ir.Param.StructUnion):
            has_outputs = any([struct_has_outputs(s) for s in sub_struct.body.alts])
        if not has_outputs:
            continue

        output_symbol = lookup.py_output_field_symbol[sub_struct.base.id_]
        output_symbol_resolved = lookup.py_symbol[sub_struct.base.id_]
        if access_via_self:
            output_symbol_resolved = lang.member_access(output_symbol_resolved)

        members[output_symbol] = lang.struct_collect_outputs(sub_struct, output_symbol_resolved)

    lang.generate_ret_object_creation(
        buf=func.body,
        execution_symbol="execution",
        output_type=lookup.py_output_type[struct.base.id_],
        members=members,
    )


def compile_interface(
    lang: LanguageProvider,
    interface: ir.Interface,
    package_scope: Scope,
    interface_module: GenericModule,
) -> None:
    """Entry point to the Python backend."""
    interface_module.imports.extend(lang.wrapper_module_imports())

    metadata_symbol = generate_static_metadata(
        lang=lang,
        module=interface_module,
        scope=package_scope,
        interface=interface,
    )
    interface_module.exports.append(metadata_symbol)

    function_symbol = package_scope.add_or_dodge(lang.ensure_var_case(interface.command.base.name))
    interface_module.exports.append(function_symbol)

    function_scope = Scope(lang).language_base_scope()
    function_scope.add_or_die("runner")
    function_scope.add_or_die("execution")
    function_scope.add_or_die("cargs")
    function_scope.add_or_die("ret")

    # Lookup tables
    lookup = LookupParam(
        lang=lang,
        interface=interface,
        package_scope=package_scope,
        function_symbol=function_symbol,
        function_scope=function_scope,
    )

    _compile_struct(
        lang=lang,
        struct=interface.command,
        interface_module=interface_module,
        lookup=lookup,
        metadata_symbol=metadata_symbol,
        root_function=True,
        stdout_as_string_output=interface.stdout_as_string_output,
        stderr_as_string_output=interface.stderr_as_string_output,
    )
