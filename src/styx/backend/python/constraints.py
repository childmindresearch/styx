import styx.ir.core as ir
from styx.backend.python.lookup import LookupParam
from styx.backend.python.pycodegen.core import LineBuffer, PyFunc, indent


def _generate_raise_value_err(obj: str, expectation: str, reality: str | None = None) -> LineBuffer:
    fstr = ""
    if "{" in obj or "{" in expectation or (reality is not None and "{" in reality):
        fstr = "f"

    return (
        [f'raise ValueError({fstr}"{obj} must be {expectation} but was {reality}")']
        if reality is not None
        else [f'raise ValueError({fstr}"{obj} must be {expectation}")']
    )


def _param_compile_constraint_checks(buf: LineBuffer, param: ir.Param, lookup: LookupParam) -> None:
    """Generate input constraint validation code for an input argument."""
    py_symbol = lookup.py_symbol[param.base.id_]

    min_value: float | int | None = None
    max_value: float | int | None = None
    list_count_min: int | None = None
    list_count_max: int | None = None

    if isinstance(param.body, (ir.Param.Float, ir.Param.Int)):
        min_value = param.body.min_value
        max_value = param.body.max_value
    elif param.list_:
        list_count_min = param.list_.count_min
        list_count_max = param.list_.count_max

    val_opt = ""
    if param.nullable:
        val_opt = f"{py_symbol} is not None and "

    # List argument length validation
    if list_count_min is not None and list_count_max is not None:
        # Case: len(list[]) == X
        assert list_count_min <= list_count_max
        if list_count_min == list_count_max:
            buf.extend([
                f"if {val_opt}(len({py_symbol}) != {list_count_min}): ",
                *indent(
                    _generate_raise_value_err(
                        f"Length of '{py_symbol}'",
                        f"{list_count_min}",
                        f"{{len({py_symbol})}}",
                    )
                ),
            ])
        else:
            # Case: X <= len(list[]) <= Y
            buf.extend([
                f"if {val_opt}not ({list_count_min} <= " f"len({py_symbol}) <= {list_count_max}): ",
                *indent(
                    _generate_raise_value_err(
                        f"Length of '{py_symbol}'",
                        f"between {list_count_min} and {list_count_max}",
                        f"{{len({py_symbol})}}",
                    )
                ),
            ])
    elif list_count_min is not None:
        # Case len(list[]) >= X
        buf.extend([
            f"if {val_opt}not ({list_count_min} <= len({py_symbol})): ",
            *indent(
                _generate_raise_value_err(
                    f"Length of '{py_symbol}'",
                    f"greater than {list_count_min}",
                    f"{{len({py_symbol})}}",
                )
            ),
        ])
    elif list_count_max is not None:
        # Case len(list[]) <= X
        buf.extend([
            f"if {val_opt}not (len({py_symbol}) <= {list_count_max}): ",
            *indent(
                _generate_raise_value_err(
                    f"Length of '{py_symbol}'",
                    f"less than {list_count_max}",
                    f"{{len({py_symbol})}}",
                )
            ),
        ])

    # Numeric argument range validation
    op_min = "<="
    op_max = "<="
    if min_value is not None and max_value is not None:
        # Case: X <= arg <= Y
        assert min_value <= max_value
        if param.list_:
            buf.extend([
                f"if {val_opt}not ({min_value} {op_min} min({py_symbol}) "
                f"and max({py_symbol}) {op_max} {max_value}): ",
                *indent(
                    _generate_raise_value_err(
                        f"All elements of '{py_symbol}'",
                        f"between {min_value} {op_min} x {op_max} {max_value}",
                    )
                ),
            ])
        else:
            buf.extend([
                f"if {val_opt}not ({min_value} {op_min} {py_symbol} {op_max} {max_value}): ",
                *indent(
                    _generate_raise_value_err(
                        f"'{py_symbol}'",
                        f"between {min_value} {op_min} x {op_max} {max_value}",
                        f"{{{py_symbol}}}",
                    )
                ),
            ])
    elif min_value is not None:
        # Case: X <= arg
        if param.list_:
            buf.extend([
                f"if {val_opt}not ({min_value} {op_min} min({py_symbol})): ",
                *indent(
                    _generate_raise_value_err(
                        f"All elements of '{py_symbol}'",
                        f"greater than {min_value} {op_min} x",
                    )
                ),
            ])
        else:
            buf.extend([
                f"if {val_opt}not ({min_value} {op_min} {py_symbol}): ",
                *indent(
                    _generate_raise_value_err(
                        f"'{py_symbol}'",
                        f"greater than {min_value} {op_min} x",
                        f"{{{py_symbol}}}",
                    )
                ),
            ])
    elif max_value is not None:
        # Case: arg <= X
        if param.list_:
            buf.extend([
                f"if {val_opt}not (max({py_symbol}) {op_max} {max_value}): ",
                *indent(
                    _generate_raise_value_err(
                        f"All elements of '{py_symbol}'",
                        f"less than x {op_max} {max_value}",
                    )
                ),
            ])
        else:
            buf.extend([
                f"if {val_opt}not ({py_symbol} {op_max} {max_value}): ",
                *indent(
                    _generate_raise_value_err(
                        f"'{py_symbol}'",
                        f"less than x {op_max} {max_value}",
                        f"{{{py_symbol}}}",
                    )
                ),
            ])


def struct_compile_constraint_checks(
    func: PyFunc,
    struct: ir.Param[ir.Param.Struct],
    lookup: LookupParam,
) -> None:
    for param in struct.body.iter_params():
        _param_compile_constraint_checks(func.body, param, lookup)
