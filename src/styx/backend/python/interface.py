import styx.ir.core as ir
from styx.backend.python.constraints import struct_compile_constraint_checks
from styx.backend.python.documentation import docs_to_docstring
from styx.backend.python.lookup import LookupParam
from styx.backend.python.metadata import generate_static_metadata
from styx.backend.python.pycodegen.core import (
    LineBuffer,
    PyArg,
    PyDataClass,
    PyFunc,
    PyModule,
    expand,
    indent,
)
from styx.backend.python.pycodegen.scope import Scope
from styx.backend.python.pycodegen.utils import as_py_literal, enquote, python_snakify
from styx.backend.python.utils import (
    param_py_default_value,
    param_py_var_is_set_by_user,
    param_py_var_to_str,
    struct_has_outputs,
)


def _compile_struct(
    struct: ir.Param[ir.Param.Struct],
    interface_module: PyModule,
    lookup: LookupParam,
    metadata_symbol: str,
    root_function: bool,
) -> None:
    has_outputs = root_function or struct_has_outputs(struct)

    outputs_type = lookup.py_output_type[struct.base.id_]

    if root_function:
        func_cargs_building = PyFunc(
            name=lookup.py_type[struct.base.id_],
            return_type=outputs_type,
            return_descr=f"NamedTuple of outputs " f"(described in `{outputs_type}`).",
            docstring_body=docs_to_docstring(struct.base.docs),
        )
        pyargs = func_cargs_building.args
    else:
        func_cargs_building = PyFunc(
            name="run",
            docstring_body="Build command line arguments. This method is called by the main command.",
            return_type="list[str]",
            return_descr="Command line arguments",
            args=[
                PyArg(name="self", type=None, default=None, docstring="The sub-command object."),
                PyArg(name="execution", type="Execution", default=None, docstring="The execution object."),
            ],
        )
        struct_class = PyDataClass(
            name=lookup.py_struct_type[struct.base.id_],
            docstring=docs_to_docstring(struct.base.docs),
            methods=[func_cargs_building],
        )
        if has_outputs:
            func_outputs = PyFunc(
                name="outputs",
                docstring_body="Collect output file paths.",
                return_type=outputs_type,
                return_descr=f"NamedTuple of outputs " f"(described in `{outputs_type}`).",
                args=[
                    PyArg(name="self", type=None, default=None, docstring="The sub-command object."),
                    PyArg(name="execution", type="Execution", default=None, docstring="The execution object."),
                ],
            )
        pyargs = struct_class.fields

    # Collect param python symbols
    for elem in struct.body.iter_params():
        symbol = lookup.py_symbol[elem.base.id_]
        pyargs.append(
            PyArg(
                name=symbol,
                type=lookup.py_type[elem.base.id_],
                default=param_py_default_value(elem),
                docstring=elem.base.docs.description,
            )
        )

        if isinstance(elem.body, ir.Param.Struct):
            _compile_struct(
                struct=elem,
                interface_module=interface_module,
                lookup=lookup,
                metadata_symbol=metadata_symbol,
                root_function=False,
            )
        elif isinstance(elem.body, ir.Param.StructUnion):
            for child in elem.body.alts:
                _compile_struct(
                    struct=child,
                    interface_module=interface_module,
                    lookup=lookup,
                    metadata_symbol=metadata_symbol,
                    root_function=False,
                )

    struct_compile_constraint_checks(func=func_cargs_building, struct=struct, lookup=lookup)

    if has_outputs:
        _compile_outputs_class(
            struct=struct,
            interface_module=interface_module,
            lookup=lookup,
        )

    if root_function:
        func_cargs_building.body.extend([
            "runner = runner or get_global_runner()",
            f"execution = runner.start_execution({metadata_symbol})",
        ])

    _compile_cargs_building(struct, lookup, func_cargs_building, access_via_self=not root_function)

    if root_function:
        pyargs.append(PyArg(name="runner", type="Runner | None", default="None", docstring="Command runner"))
        _compile_outputs_building(
            struct=struct,
            func=func_cargs_building,
            lookup=lookup,
            access_via_self=False,
        )
        func_cargs_building.body.extend([
            "execution.run(cargs)",
            "return ret",
        ])
        interface_module.funcs_and_classes.append(func_cargs_building)
    else:
        if has_outputs:
            _compile_outputs_building(
                struct=struct,
                func=func_outputs,
                lookup=lookup,
                access_via_self=True,
            )
            func_outputs.body.extend([
                "return ret",
            ])
            struct_class.methods.append(func_outputs)
        func_cargs_building.body.extend([
            "return cargs",
        ])
        interface_module.funcs_and_classes.append(struct_class)
        interface_module.exports.append(struct_class.name)


def _compile_cargs_building(
    param: ir.Param[ir.Param.Struct],
    lookup: LookupParam,
    func: PyFunc,
    access_via_self: bool,
) -> None:
    func.body.append("cargs = []")

    for group in param.body.groups:
        group_conditions_py = []

        building_cargs_py: list[tuple[str, bool]] = []
        for carg in group.cargs:
            building_carg_py: list[tuple[str, bool]] = []
            for token in carg.tokens:
                if isinstance(token, str):
                    building_carg_py.append((as_py_literal(token), False))
                    continue
                elem_symbol = lookup.py_symbol[token.base.id_]
                if access_via_self:
                    elem_symbol = f"self.{elem_symbol}"
                building_carg_py.append(param_py_var_to_str(token, elem_symbol))
                if (py_var_is_set_by_user := param_py_var_is_set_by_user(token, elem_symbol, False)) is not None:
                    group_conditions_py.append(py_var_is_set_by_user)

            if len(building_carg_py) == 1:
                building_cargs_py.append(building_carg_py[0])
            else:
                destructured = [s if not s_is_list else f'" ".join({s})' for s, s_is_list in building_carg_py]
                building_cargs_py.append((" + ".join(destructured), False))

        buf_appending: LineBuffer = []

        if len(building_cargs_py) == 1:
            for val, val_is_list in building_cargs_py:
                if val_is_list:
                    buf_appending.append(f"cargs.extend({val})")
                else:
                    buf_appending.append(f"cargs.append({val})")
        else:
            x = [(f"*{val}" if val_is_list else val) for val, val_is_list in building_cargs_py]
            buf_appending.extend([
                "cargs.extend([",
                *indent(expand(",\n".join(x))),
                "])",
            ])

        if len(group_conditions_py) > 0:
            func.body.append(f"if {' and '.join(group_conditions_py)}:")
            func.body.extend(indent(buf_appending))
        else:
            func.body.extend(buf_appending)


def _compile_outputs_class(
    struct: ir.Param[ir.Param.Struct],
    interface_module: PyModule,
    lookup: LookupParam,
) -> None:
    outputs_class = PyDataClass(
        name=lookup.py_output_type[struct.base.id_],
        docstring=f"Output object returned when calling `{lookup.py_type[struct.base.id_]}(...)`.",
        is_named_tuple=True,
    )
    outputs_class.fields.append(
        PyArg(
            name="root",
            type="OutputPathType",
            default=None,
            docstring="Output root folder. This is the root folder for all outputs.",
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

        if not optional:
            output_type = "OutputPathType"
        else:
            output_type = "OutputPathType | None"

        outputs_class.fields.append(
            PyArg(
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
                    output_type = f"typing.List[{output_type}]"
                if sub_struct.nullable:
                    output_type = f"{output_type} | None"

                output_symbol = lookup.py_output_field_symbol[sub_struct.base.id_]

                input_type = lookup.py_struct_type[sub_struct.base.id_]
                docs_append = ""
                if sub_struct.list_:
                    docs_append = "This is a list of outputs with the same length and order as the inputs."

                outputs_class.fields.append(
                    PyArg(
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
                    output_type = ", ".join(alt_types)
                    output_type = f"typing.Union[{output_type}]"

                    if sub_struct.list_:
                        output_type = f"typing.List[{output_type}]"
                    if sub_struct.nullable:
                        output_type = f"{output_type} | None"

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
                        PyArg(
                            name=output_symbol,
                            type=output_type,
                            default=None,
                            docstring=f"Outputs from {input_types_human}.{docs_append}",
                        )
                    )

    interface_module.funcs_and_classes.append(outputs_class)
    interface_module.exports.append(outputs_class.name)


def _compile_outputs_building(
    struct: ir.Param[ir.Param.Struct],
    func: PyFunc,
    lookup: LookupParam,
    access_via_self: bool = False,
) -> None:
    """Generate the outputs building code."""
    func.body.append(f"ret = {lookup.py_output_type[struct.base.id_]}(")

    # Set root output path
    func.body.extend(indent(['root=execution.output_file("."),']))

    def _py_get_val(
        output_param_reference: ir.OutputParamReference,
    ) -> str:
        param = lookup.param[output_param_reference.ref_id]
        symbol = lookup.py_symbol[param.base.id_]

        substitute = symbol
        if access_via_self:
            substitute = f"self.{substitute}"

        if param.list_:
            raise Exception(f"Output path template replacements cannot be lists. ({param.base.name})")

        if isinstance(param.body, ir.Param.String):
            for suffix in output_param_reference.file_remove_suffixes:
                substitute += f".removesuffix({as_py_literal(suffix)})"
            return substitute

        if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
            return f"str({substitute})"

        if isinstance(param.body, ir.Param.File):
            re = f"pathlib.Path({substitute}).name"
            for suffix in output_param_reference.file_remove_suffixes:
                re += f".removesuffix({as_py_literal(suffix)})"
            return re

        if isinstance(param.body, ir.Param.Bool):
            raise Exception(f"Unsupported input type " f"for output path template of '{param.base.name}'.")
        assert False

    for output in struct.base.outputs:
        output_symbol = lookup.py_output_field_symbol[output.id_]

        output_segments: list[str] = []
        conditions = []
        for token in output.tokens:
            if isinstance(token, str):
                output_segments.append(as_py_literal(token))
                continue
            output_segments.append(_py_get_val(token))

            ostruct = lookup.param[token.ref_id]
            param_symbol = lookup.py_symbol[ostruct.base.id_]
            if (py_var_is_set_by_user := param_py_var_is_set_by_user(ostruct, param_symbol, False)) is not None:
                conditions.append(py_var_is_set_by_user)

        condition_py = ""
        if len(conditions) > 0:
            condition_py = " and ".join(conditions)
            condition_py = f" if ({condition_py}) else None"

        func.body.extend(
            indent([f"{output_symbol}=execution.output_file({' + '.join(output_segments)}){condition_py},"])
        )

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
            output_symbol_resolved = f"self.{output_symbol_resolved}"

        if sub_struct.list_:
            opt = ""
            if sub_struct.nullable:
                opt = f" if {output_symbol_resolved} else None"
            # Need to check for attr because some alts might have outputs others not.
            # todo: think about alternative solutions
            func.body.extend(
                indent([
                    f"{output_symbol}="
                    f'[i.outputs(execution) if hasattr(i, "outputs") else None for i in {output_symbol_resolved}]{opt},'
                ])
            )
        else:
            o = f"{output_symbol_resolved}.outputs(execution)"
            if sub_struct.nullable:
                o = f"{o} if {output_symbol_resolved} else None"
            func.body.extend(indent([f"{output_symbol}={o},"]))

    func.body.extend([")"])


def compile_interface(
    interface: ir.Interface,
    package_scope: Scope,
    interface_module: PyModule,
) -> None:
    """Entry point to the Python backend."""
    interface_module.imports.extend([
        "import typing",
        "import pathlib",
        "from styxdefs import *",
        "import dataclasses",
    ])

    metadata_symbol = generate_static_metadata(
        module=interface_module,
        scope=package_scope,
        interface=interface,
    )
    interface_module.exports.append(metadata_symbol)

    function_symbol = package_scope.add_or_dodge(python_snakify(interface.command.base.name))
    interface_module.exports.append(function_symbol)

    function_scope = Scope(parent=Scope.python())
    function_scope.add_or_die("runner")
    function_scope.add_or_die("execution")
    function_scope.add_or_die("cargs")
    function_scope.add_or_die("ret")

    # Lookup tables
    lookup = LookupParam(
        interface=interface,
        package_scope=package_scope,
        function_symbol=function_symbol,
        function_scope=function_scope,
    )

    _compile_struct(
        struct=interface.command,
        interface_module=interface_module,
        lookup=lookup,
        metadata_symbol=metadata_symbol,
        root_function=True,
    )
