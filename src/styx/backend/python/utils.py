import styx.ir.core as ir
from styx.backend.python.pycodegen.utils import as_py_literal, enquote


def param_py_type(param: ir.Param, lookup_struct_type: dict[ir.IdType, str]) -> str:
    """Return the Python type expression for a param.

    Args:
        param: The param.
        lookup_struct_type: lookup dictionary for struct types (pre-compute).

    Returns:
        Python type expression.
    """

    def _base() -> str:
        if isinstance(param.body, ir.Param.String):
            if param.choices:
                return f"typing.Literal[{', '.join(map(as_py_literal, param.choices))}]"
            return "str"
        if isinstance(param.body, ir.Param.Int):
            if param.choices:
                return f"typing.Literal[{', '.join(map(as_py_literal, param.choices))}]"
            return "int"
        if isinstance(param.body, ir.Param.Float):
            return "float"
        if isinstance(param.body, ir.Param.File):
            return "InputPathType"
        if isinstance(param.body, ir.Param.Bool):
            return "bool"
        if isinstance(param.body, ir.Param.Struct):
            return lookup_struct_type[param.base.id_]
        if isinstance(param.body, ir.Param.StructUnion):
            return f"typing.Union[{', '.join(lookup_struct_type[i.base.id_] for i in param.body.alts)}]"
        assert False

    type_ = _base()
    if param.list_:
        type_ = f"list[{type_}]"
    if param.nullable:
        type_ = f"{type_} | None"

    return type_


def param_py_var_to_str(
    param: ir.Param,
    symbol: str,
) -> tuple[str, bool]:
    """Python var to str.

    Return a Python expression that converts the variable to a string or string array
    and a boolean that indicates if the expression value is an array.
    """

    def _val() -> tuple[str, bool]:
        if not param.list_:
            if isinstance(param.body, ir.Param.String):
                return symbol, False
            if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
                return f"str({symbol})", False
            if isinstance(param.body, ir.Param.Bool):
                as_list = (len(param.body.value_true) > 1) or (len(param.body.value_false) > 1)
                if as_list:
                    value_true: str | list[str] | None = param.body.value_true
                    value_false: str | list[str] | None = param.body.value_false
                else:
                    value_true = param.body.value_true[0] if len(param.body.value_true) > 0 else None
                    value_false = param.body.value_false[0] if len(param.body.value_false) > 0 else None
                if len(param.body.value_true) > 0:
                    if len(param.body.value_false) > 0:
                        return f"({as_py_literal(value_true)} if {symbol} else {as_py_literal(value_true)})", as_list
                    return as_py_literal(value_true), as_list
                assert len(param.body.value_false) > 0
                return as_py_literal(value_false), as_list
            if isinstance(param.body, ir.Param.File):
                extra_args = ""
                if param.body.resolve_parent:
                    extra_args += ", resolve_parent=True"
                if param.body.mutable:
                    extra_args += ", mutable=True"
                return f"execution.input_file({symbol}{extra_args})", False
            if isinstance(param.body, (ir.Param.Struct, ir.Param.StructUnion)):
                return f"{symbol}.run(execution)", True
            assert False

        if param.list_.join is None:
            if isinstance(param.body, ir.Param.String):
                return symbol, True
            if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
                return f"map(str, {symbol})", True
            if isinstance(param.body, ir.Param.Bool):
                assert False, "TODO: Not implemented yet"
            if isinstance(param.body, ir.Param.File):
                extra_args = ""
                if param.body.resolve_parent:
                    extra_args += ", resolve_parent=True"
                if param.body.mutable:
                    extra_args += ", mutable=True"
                return f"[execution.input_file(f{extra_args}) for f in {symbol}]", True
            if isinstance(param.body, (ir.Param.Struct, ir.Param.StructUnion)):
                return f"[a for c in [s.run(execution) for s in {symbol}] for a in c]", True
            assert False

        # arg.data.list_separator is not None
        sep_join = f"{enquote(param.list_.join)}.join"
        if isinstance(param.body, ir.Param.String):
            return f"{sep_join}({symbol})", False
        if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
            return f"{sep_join}(map(str, {symbol}))", False
        if isinstance(param.body, ir.Param.Bool):
            assert False, "TODO: Not implemented yet"
        if isinstance(param.body, ir.Param.File):
            extra_args = ""
            if param.body.resolve_parent:
                extra_args += ", resolve_parent=True"
            if param.body.mutable:
                extra_args += ", mutable=True"
            return f"{sep_join}([execution.input_file(f{extra_args}) for f in {symbol}])", False
        if isinstance(param.body, (ir.Param.Struct, ir.Param.StructUnion)):
            return f"{sep_join}([a for c in [s.run(execution) for s in {symbol}] for a in c])", False
        assert False

    return _val()


def param_py_default_value(param: ir.Param) -> str | None:
    if param.default_value is ir.Param.SetToNone:
        return "None"
    if param.default_value is None:
        return None
    return as_py_literal(param.default_value)  # type: ignore


def param_py_var_is_set_by_user(
    param: ir.Param,
    symbol: str,
    enbrace_statement: bool = False,
) -> str | None:
    """Return a Python expression that checks if the variable is set by the user.

    Returns `None` if the param must always be specified.
    """
    if param.nullable:
        if enbrace_statement:
            return f"({symbol} is not None)"
        return f"{symbol} is not None"

    if isinstance(param.body, ir.Param.Bool):
        if len(param.body.value_true) > 0 and len(param.body.value_false) == 0:
            return symbol
        if len(param.body.value_false) > 0 and len(param.body.value_true) == 0:
            if enbrace_statement:
                return f"(not {symbol})"
            return f"not {symbol}"
    return None


def struct_has_outputs(struct: ir.Param[ir.Param.Struct]) -> bool:
    """Check if the sub-command has outputs."""
    if len(struct.base.outputs) > 0:
        return True
    for p in struct.body.iter_params():
        if isinstance(p.body, ir.Param.Struct):
            if struct_has_outputs(p):
                return True
        if isinstance(p.body, ir.Param.StructUnion):
            for struct in p.body.alts:
                if struct_has_outputs(struct):
                    return True
    return False
