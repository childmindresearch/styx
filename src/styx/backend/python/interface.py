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
    blank_before,
    expand,
    indent,
)
from styx.backend.python.pycodegen.scope import Scope
from styx.backend.python.pycodegen.utils import as_py_literal, python_snakify
from styx.backend.python.utils import (
    param_py_default_value,
    param_py_var_is_set_by_user,
    param_py_var_to_str,
    struct_has_outputs,
)


def _compile_struct(
    param: ir.IStruct | ir.IParam,
    interface_module: PyModule,
    lookup: LookupParam,
    metadata_symbol: str,
    root_function: bool,
) -> None:
    has_outputs = struct_has_outputs(param)
    if has_outputs:
        _compile_outputs_class(
            param=param,
            interface_module=interface_module,
            lookup=lookup,
        )

    outputs_type = lookup.py_output_type[param.param.id_]

    if root_function:
        func_cargs_building = PyFunc(
            name=lookup.py_type[param.param.id_],
            return_type=outputs_type,
            return_descr=f"NamedTuple of outputs " f"(described in `{outputs_type}`).",
            docstring_body=docs_to_docstring(param.param.docs),
        )
        pyargs = func_cargs_building.args
    else:
        func_cargs_building = PyFunc(
            name="run",
            docstring_body="Build command line arguments. This method is called by the main command.",
            return_type="list[str]",
            return_descr=None,
            args=[
                PyArg(name="self", type=None, default=None, docstring="The sub-command object."),
                PyArg(name="execution", type="Execution", default=None, docstring="The execution object."),
            ],
        )
        struct_class = PyDataClass(
            name=lookup.py_type[param.param.id_],
            docstring=docs_to_docstring(param.param.docs),
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
            struct_class.methods.append(func_outputs)
        pyargs = struct_class.fields

    # Collect param python symbols
    for elem in param.struct.iter_params():
        symbol = lookup.py_symbol[elem.param.id_]
        pyargs.append(
            PyArg(
                name=symbol,
                type=lookup.py_type[elem.param.id_],
                default=param_py_default_value(elem),
                docstring=elem.param.docs.description,
            )
        )

        if isinstance(elem, ir.IStruct):
            _compile_struct(
                param=elem,
                interface_module=interface_module,
                lookup=lookup,
                metadata_symbol=metadata_symbol,
                root_function=False,
            )
        elif isinstance(elem, ir.IStructUnion):
            for child in elem.alts:
                _compile_struct(
                    param=child,
                    interface_module=interface_module,
                    lookup=lookup,
                    metadata_symbol=metadata_symbol,
                    root_function=False,
                )

    struct_compile_constraint_checks(func=func_cargs_building, struct=param, lookup=lookup)

    func_cargs_building.body.extend([
        "runner = runner or get_global_runner()",
        f"execution = runner.start_execution({metadata_symbol})",
    ])

    _compile_cargs_building(param, lookup, func_cargs_building, access_via_self=not root_function)

    if root_function:
        pyargs.append(PyArg(name="runner", type="Runner | None", default="None", docstring="Command runner"))
        _compile_outputs_building(
            param=param,
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
                param=param,
                func=func_outputs,
                lookup=lookup,
                access_via_self=True,
            )
            func_outputs.body.extend([
                "return ret",
            ])
        func_cargs_building.body.extend([
            "return cargs",
        ])
        interface_module.funcs_and_classes.append(struct_class)


def _compile_cargs_building(
    param: ir.IParam | ir.IStruct,
    lookup: LookupParam,
    func: PyFunc,
    access_via_self: bool,
) -> None:
    func.body.append("cargs = []")

    for group in param.struct.groups:
        group_conditions_py = []

        building_cargs_py: list[tuple[str, bool]] = []
        for carg in group.cargs:
            building_carg_py: list[tuple[str, bool]] = []
            for token in carg.tokens:
                if isinstance(token, str):
                    building_carg_py.append((as_py_literal(token), False))
                    continue
                elem_symbol = lookup.py_symbol[token.param.id_]
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
    param: ir.IStruct | ir.IParam,
    interface_module: PyModule,
    lookup: LookupParam,
) -> None:
    outputs_class = PyDataClass(
        name=lookup.py_output_type[param.param.id_],
        docstring=f"Output object returned when calling `{lookup.py_type[param.param.id_]}(...)`.",
    )
    outputs_class.fields.append(
        PyArg(
            name="root",
            type="OutputPathType",
            default=None,
            docstring="Output root folder. This is the root folder for all outputs.",
        )
    )

    for output in param.param.outputs:
        output_symbol = lookup.py_output_field_symbol[output.id_]

        # Optional if any of its param references is optional
        optional = False
        for token in output.tokens:
            if isinstance(token, str):
                continue
            optional = optional or isinstance(lookup.param[token.ref_id], ir.IOptional)

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

    interface_module.header.extend(blank_before(outputs_class.generate(True), 2))
    interface_module.exports.append(outputs_class.name)


def _compile_outputs_building(
    param: ir.IStruct | ir.IParam,
    func: PyFunc,
    lookup: LookupParam,
    access_via_self: bool = False,
) -> None:
    """Generate the outputs building code."""
    func.body.append(f"ret = {lookup.py_output_type[param.param.id_]}(")

    # Set root output path
    func.body.extend(indent(['root=execution.output_file("."),']))

    def _py_get_val(
        output_param_reference: ir.OutputParamReference,
    ) -> str:
        param = lookup.param[output_param_reference.ref_id]
        symbol = lookup.py_symbol[param.param.id_]

        substitute = symbol
        if access_via_self:
            substitute = f"self.{substitute}"

        if isinstance(param, ir.IList):
            raise Exception(f"Output path template replacements cannot be lists. ({param.param.name})")

        if isinstance(param, ir.IStr):
            return substitute

        if isinstance(param, (ir.IInt, ir.IFloat)):
            return f"str({substitute})"

        if isinstance(param, ir.IFile):
            re = f"pathlib.Path({substitute}).name"
            for suffix in output_param_reference.file_remove_suffixes:
                re += f".removesuffix({as_py_literal(suffix)})"
            return re

        if isinstance(param, ir.IBool):
            raise Exception(f"Unsupported input type " f"for output path template of '{param.param.name}'.")
        assert False

    for output in param.param.outputs:
        output_symbol = lookup.py_output_field_symbol[output.id_]

        output_segments: list[str] = []
        conditions = []
        for token in output.tokens:
            if isinstance(token, str):
                output_segments.append(as_py_literal(token))
                continue
            output_segments.append(_py_get_val(token))

            param = lookup.param[token.ref_id]
            param_symbol = lookup.py_symbol[param.param.id_]
            if (py_var_is_set_by_user := param_py_var_is_set_by_user(param, param_symbol, False)) is not None:
                conditions.append(py_var_is_set_by_user)

        condition_py = ""
        if len(conditions) > 0:
            condition_py = " and ".join(conditions)
            condition_py = f" if ({condition_py}) else None"

        func.body.extend(
            indent([f"{output_symbol}=execution.output_file({' + '.join(output_segments)}){condition_py},"])
        )

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

    function_symbol = package_scope.add_or_dodge(python_snakify(interface.command.param.name))
    interface_module.exports.append(function_symbol)

    function_scope = Scope(parent=package_scope)
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
        param=interface.command,
        interface_module=interface_module,
        lookup=lookup,
        metadata_symbol=metadata_symbol,
        root_function=True,
    )
