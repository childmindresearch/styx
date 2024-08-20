from styx.ir.core import Interface, Expression, ExpressionSequence, ExpressionAlternation, StringParameter, \
    FloatParameter, IntegerParameter, FileParameter


def _expr_counter(expr: Expression) -> int:
    match expr.body:
        case ExpressionSequence():
            return 1 + sum([_expr_counter(e) for e in expr.body.elements])
        case ExpressionAlternation():
            return 1 + sum([_expr_counter(e) for e in expr.body.alternatives])
    return 1


def _param_counter(expr: Expression) -> int:
    match expr.body:
        case ExpressionSequence():
            return sum([_param_counter(e) for e in expr.body.elements])
        case ExpressionAlternation():
            return sum([_param_counter(e) for e in expr.body.alternatives])
        case IntegerParameter():
            return 1
        case FloatParameter():
            return 1
        case StringParameter():
            return 1
        case FileParameter():
            return 1
    return 0


def _mccabe(expr: Expression) -> int:
    complexity = 1
    if expr.required is not True or expr.repeatable:
        complexity = 2

    match expr.body:
        case ExpressionSequence():
            x = [_mccabe(e) for e in expr.body.elements]
            return complexity * (sum(x) - len(x) + 1)
        case ExpressionAlternation():
            return complexity * sum([_mccabe(e) for e in expr.body.alternatives])
    return complexity


def stats(interface: Interface) -> dict[str, str | int | float]:
    return {
        "name": interface.expression.name,
        "num_expressions": _expr_counter(interface.expression),
        "num_params": _param_counter(interface.expression),
        "mccabe": _mccabe(interface.expression)
    }
