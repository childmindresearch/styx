from styx.model.core import GroupConstraint, InputArgument, InputTypePrimitive, WithSymbol
from styx.pycodegen.core import LineBuffer, expand, indent
from styx.pycodegen.utils import enquote


def _generate_raise_value_err(obj: str, expectation: str, reality: str | None = None) -> LineBuffer:
    fstr = ""
    if "{" in obj or "{" in expectation or (reality is not None and "{" in reality):
        fstr = "f"

    return (
        [f'raise ValueError({fstr}"{obj} must be {expectation} but was {reality}")']
        if reality is not None
        else [f'raise ValueError({fstr}"{obj} must be {expectation}")']
    )


def generate_input_constraint_validation(
    buf: LineBuffer,
    input_: WithSymbol[InputArgument],
) -> None:
    """Generate input constraint validation code for an input argument."""
    py_symbol = input_.symbol
    constraints = input_.data.constraints

    val_opt = ""
    if input_.data.type.is_optional:
        val_opt = f"{py_symbol} is not None and "

    # List argument length validation
    if constraints.list_length_min is not None and constraints.list_length_max is not None:
        # Case: len(list[]) == X
        assert constraints.list_length_min <= constraints.list_length_max
        if constraints.list_length_min == constraints.list_length_max:
            buf.extend([
                f"if {val_opt}(len({py_symbol}) != {constraints.list_length_min}): ",
                *indent(
                    _generate_raise_value_err(
                        f"Length of '{py_symbol}'",
                        f"{constraints.list_length_min}",
                        f"{{len({py_symbol})}}",
                    )
                ),
            ])
        else:
            # Case: X <= len(list[]) <= Y
            buf.extend([
                f"if {val_opt}not ({constraints.list_length_min} <= "
                f"len({py_symbol}) <= {constraints.list_length_max}): ",
                *indent(
                    _generate_raise_value_err(
                        f"Length of '{py_symbol}'",
                        f"between {constraints.list_length_min} and {constraints.list_length_max}",
                        f"{{len({py_symbol})}}",
                    )
                ),
            ])
    elif constraints.list_length_min is not None:
        # Case len(list[]) >= X
        buf.extend([
            f"if {val_opt}not ({constraints.list_length_min} <= len({py_symbol})): ",
            *indent(
                _generate_raise_value_err(
                    f"Length of '{py_symbol}'",
                    f"greater than {constraints.list_length_min}",
                    f"{{len({py_symbol})}}",
                )
            ),
        ])
    elif constraints.list_length_max is not None:
        # Case len(list[]) <= X
        buf.extend([
            f"if {val_opt}not (len({py_symbol}) <= {constraints.list_length_max}): ",
            *indent(
                _generate_raise_value_err(
                    f"Length of '{py_symbol}'",
                    f"less than {constraints.list_length_max}",
                    f"{{len({py_symbol})}}",
                )
            ),
        ])

    # Numeric argument range validation
    op_min = "<" if constraints.value_min_exclusive else "<="
    op_max = "<" if constraints.value_max_exclusive else "<="
    if constraints.value_min is not None and constraints.value_max is not None:
        # Case: X <= arg <= Y
        assert constraints.value_min <= constraints.value_max
        if input_.data.type.is_list:
            buf.extend([
                f"if {val_opt}not ({constraints.value_min} {op_min} min({py_symbol}) "
                f"and max({py_symbol}) {op_max} {constraints.value_max}): ",
                *indent(
                    _generate_raise_value_err(
                        f"All elements of '{py_symbol}'",
                        f"between {constraints.value_min} {op_min} x {op_max} {constraints.value_max}",
                    )
                ),
            ])
        else:
            buf.extend([
                f"if {val_opt}not ({constraints.value_min} {op_min} {py_symbol} {op_max} {constraints.value_max}): ",
                *indent(
                    _generate_raise_value_err(
                        f"'{py_symbol}'",
                        f"between {constraints.value_min} {op_min} x {op_max} {constraints.value_max}",
                        f"{{{py_symbol}}}",
                    )
                ),
            ])
    elif constraints.value_min is not None:
        # Case: X <= arg
        if input_.data.type.is_list:
            buf.extend([
                f"if {val_opt}not ({constraints.value_min} {op_min} min({py_symbol})): ",
                *indent(
                    _generate_raise_value_err(
                        f"All elements of '{py_symbol}'",
                        f"greater than {constraints.value_min} {op_min} x",
                    )
                ),
            ])
        else:
            buf.extend([
                f"if {val_opt}not ({constraints.value_min} {op_min} {py_symbol}): ",
                *indent(
                    _generate_raise_value_err(
                        f"'{py_symbol}'",
                        f"greater than {constraints.value_min} {op_min} x",
                        f"{{{py_symbol}}}",
                    )
                ),
            ])
    elif constraints.value_max is not None:
        # Case: arg <= X
        if input_.data.type.is_list:
            buf.extend([
                f"if {val_opt}not (max({py_symbol}) {op_max} {constraints.value_max}): ",
                *indent(
                    _generate_raise_value_err(
                        f"All elements of '{py_symbol}'",
                        f"less than x {op_max} {constraints.value_max}",
                    )
                ),
            ])
        else:
            buf.extend([
                f"if {val_opt}not ({py_symbol} {op_max} {constraints.value_max}): ",
                *indent(
                    _generate_raise_value_err(
                        f"'{py_symbol}'",
                        f"less than x {op_max} {constraints.value_max}",
                        f"{{{py_symbol}}}",
                    )
                ),
            ])


def _input_argument_to_py_expr_is_set(input_: WithSymbol[InputArgument]) -> str:
    """Return a Python expression that checks if the input is set."""
    if input_.data.type.primitive == InputTypePrimitive.Flag:
        return input_.symbol
    return f"({input_.symbol} is not None)"


def generate_group_constraint_validation(
    buf: LineBuffer,
    group: GroupConstraint,  # type: ignore
    args_lookup: dict[str, WithSymbol[InputArgument]],
) -> None:
    group_args = [args_lookup[x] for x in group.members]
    if group.members_mutually_exclusive:
        txt_members = [enquote(x) for x in expand(",\\n\n".join(group.members))]
        check_members = expand(" +\n".join([_input_argument_to_py_expr_is_set(x) for x in group_args]))
        buf.extend(["if ("])
        buf.extend(indent(check_members))
        buf.extend([
            ") > 1:",
            *indent([
                "raise ValueError(",
                *indent([
                    '"Only one of the following arguments can be specified:\\n"',
                    *txt_members,
                ]),
                ")",
            ]),
        ])
    if group.members_must_include_all_or_none:
        txt_members = [enquote(x) for x in expand(",\\n\n".join(group.members))]
        check_members = expand(" ==\n".join([_input_argument_to_py_expr_is_set(x) for x in group_args]))
        buf.extend(["if not ("])
        buf.extend(indent(check_members))
        buf.extend([
            "):",
            *indent([
                "raise ValueError(",
                *indent([
                    '"All or none of the following arguments must be specified:\\n"',
                    *txt_members,
                ]),
                ")",
            ]),
        ])
    if group.members_must_include_one:
        txt_members = [enquote("- " + x) for x in expand("\\n\n".join(group.members))]
        check_members = expand(" or\n".join([_input_argument_to_py_expr_is_set(x) for x in group_args]))
        buf.extend(["if not ("])
        buf.extend(indent(check_members))
        buf.extend([
            "):",
            *indent([
                "raise ValueError(",
                *indent([
                    '"One of the following arguments must be specified:\\n"',
                    *txt_members,
                ]),
                ")",
            ]),
        ])
