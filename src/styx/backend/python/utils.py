from typing import Any, Generator

import styx.ir.core as ir
from styx.backend.python.pycodegen.utils import as_py_literal, enquote


def iter_params_recursively(param: ir.IParam | str, skip_self: bool = True) -> Generator[ir.IParam, Any, None]:
    """Iterate through all child-params recursively."""
    if isinstance(param, str):
        return
    if not skip_self:
        yield param
    if isinstance(param, ir.IStruct):
        for e in param.struct.iter_params():
            yield from iter_params_recursively(e, False)
    elif isinstance(param, ir.IStructUnion):
        for e in param.alts:
            yield from iter_params_recursively(e, False)


def param_py_type(param: ir.IParam, lookup_struct_type: dict[ir.IdType, str]) -> str:
    """Return the Python type expression for a param.

    Args:
        param: The param.
        lookup_struct_type: lookup dictionary for struct types (pre-compute).

    Returns:
        Python type expression.
    """

    def _base() -> str:
        if isinstance(param, ir.IStr):
            if param.choices:
                return f"typing.Literal[{', '.join(map(as_py_literal, param.choices))}]"
            return "str"
        if isinstance(param, ir.IInt):
            if param.choices:
                return f"typing.Literal[{', '.join(map(as_py_literal, param.choices))}]"
            return "str"
        if isinstance(param, ir.IFloat):
            return "float"
        if isinstance(param, ir.IFile):
            return "InputPathType"
        if isinstance(param, ir.IBool):
            return "bool"
        if isinstance(param, ir.IStruct):
            return lookup_struct_type[param.param.id_]
        if isinstance(param, ir.IStructUnion):
            return f"typing.Union[{', '.join(lookup_struct_type[i.param.id_] for i in param.alts)}]"
        assert False

    type_ = _base()
    if isinstance(param, ir.IList):
        type_ = f"list[{type_}]"
    if isinstance(param, ir.IOptional):
        type_ = f"{type_} | None"
    return type_


def param_py_var_to_str(
    param: ir.IParam,
    symbol: str,
) -> tuple[str, bool]:
    """Return a Python expression that converts the variable to a string or string array
    and a boolean that indicates if the expression value is an array.
    """

    def _val() -> tuple[str, bool]:
        if not isinstance(param, ir.IList):
            if isinstance(param, ir.IStr):
                return symbol, False
            if isinstance(param, (ir.IInt, ir.IFloat)):
                return f"str({symbol})", False
            if isinstance(param, ir.IBool):
                as_list = (len(param.value_true) > 1) or (len(param.value_false) > 1)
                if as_list:
                    value_true = param.value_true
                    value_false = param.value_false
                else:
                    value_true = param.value_true[0] if len(param.value_true) > 0 else None
                    value_false = param.value_false[0] if len(param.value_false) > 0 else None
                if len(param.value_true) > 0:
                    if len(param.value_false) > 0:
                        return f"({as_py_literal(value_true)} if {symbol} else {as_py_literal(value_true)})", as_list
                    return as_py_literal(value_true), as_list
                assert len(param.value_false) > 0
                return as_py_literal(value_false), as_list
            if isinstance(param, ir.IFile):
                return f"execution.input_file({symbol})", False
            if isinstance(param, (ir.IStruct, ir.IStructUnion)):
                return f"{symbol}.run(execution)", True
            assert False

        if param.list_.join is None:
            if isinstance(param, ir.IStr):
                return symbol, True
            if isinstance(param, (ir.IInt, ir.IFloat)):
                return f"map(str, {symbol})", True
            if isinstance(param, ir.IBool):
                assert False, "TODO: Not implemented yet"
            if isinstance(param, ir.IFile):
                return f"[execution.input_file(f) for f in {symbol}]", True
            if isinstance(param, (ir.IStruct, ir.IStructUnion)):
                return f"[a for c in [s.run(execution) for s in {symbol}] for a in c]", True
            assert False

        # arg.data.list_separator is not None
        sep_join = f"{enquote(param.list_.join)}.join"
        if isinstance(param, ir.IStr):
            return f"{sep_join}({symbol})", False
        if isinstance(param, (ir.IInt, ir.IFloat)):
            return f"{sep_join}(map(str, {symbol}))", False
        if isinstance(param, ir.IBool):
            assert False, "TODO: Not implemented yet"
        if isinstance(param, ir.IFile):
            return f"{sep_join}([execution.input_file(f) for f in {symbol}])", False
        if isinstance(param, (ir.IStruct, ir.IStructUnion)):
            return f"{sep_join}([a for c in [s.run(execution) for s in {symbol}] for a in c])", False
        assert False

    return _val()


def param_py_default_value(param: ir.IParam) -> str | None:
    # Is this cheating? Maybe.

    if hasattr(param, "default_value"):
        if param.default_value is ir.IOptional.SetToNone:
            return "None"
        if param.default_value is None:
            return None
        return as_py_literal(param.default_value)

    if hasattr(param, "default_value_set_to_none"):
        if param.default_value_set_to_none:
            return "None"
        return None


def param_py_var_is_set_by_user(
    param: ir.IParam,
    symbol: str,
    enbrace_statement: bool = False,
) -> str | None:
    """Return a Python expression that checks if the variable is set by the user.

    Returns `None` if the param must always be specified.
    """
    if isinstance(param, ir.IOptional):
        if enbrace_statement:
            return f"({symbol} is not None)"
        return f"{symbol} is not None"

    if isinstance(param, ir.IBool):
        if len(param.value_true) > 0 and len(param.value_false) == 0:
            return symbol
        if len(param.value_false) > 0 and len(param.value_true) == 0:
            if enbrace_statement:
                return f"(not {symbol})"
            return f"not {symbol}"
    return None


def struct_has_outputs(struct: ir.IParam | ir.IStruct) -> bool:
    """Check if the sub-command has outputs."""
    if len(struct.param.outputs) > 0:
        return True
    for p in struct.struct.iter_params():
        if isinstance(p, ir.IStruct):
            if struct_has_outputs(p):
                return True
        if isinstance(p, ir.IStructUnion):
            for struct in p.alts:
                if struct_has_outputs(struct):
                    return True
    return False
