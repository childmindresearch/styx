import styx.ir.core as ir


def _expr_counter(expr: ir.IParam) -> int:
    if isinstance(expr, ir.IStruct):
        return 1 + sum([_expr_counter(e) for e in expr.struct.iter_params()])
    if isinstance(expr, ir.IStructUnion):
        return 1 + sum([_expr_counter(e) for e in expr.alts])
    return 1


def _param_counter(expr: ir.IParam) -> int:
    if isinstance(expr, ir.IStruct):
        return sum([_param_counter(e) for e in expr.struct.iter_params()])
    if isinstance(expr, ir.IStructUnion):
        return sum([_param_counter(e) for e in expr.alts])
    return 1


def _mccabe(expr: ir.IParam) -> int:
    complexity = 1

    if isinstance(expr, ir.IOptional) or (
        isinstance(expr, (ir.IStruct, ir.IStructUnion)) and isinstance(expr, ir.IList)
    ):
        complexity = 2

    match expr:
        case ir.IStruct():
            x = [_mccabe(e) for e in expr.struct.iter_params()]
            return complexity * (sum(x) - len(x) + 1)
        case ir.IStructUnion():
            return complexity * sum([_mccabe(e) for e in expr.alts])
    return complexity


def stats(interface: ir.Interface) -> dict[str, str | int | float]:
    return {
        "name": interface.command.param.name,
        "num_expressions": _expr_counter(interface.command),
        "num_params": _param_counter(interface.command),
        "mccabe": _mccabe(interface.command),
    }
