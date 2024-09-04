from styx.ir.core import Expression


# todo:
# Likely optimizations:
#  - Find nested required=True repeated=False expressions and merge them
#  - Find neighbouring ConstantParameters in ExpressionSequences and merge them
#  - Find min 0 max 1 repetitions and convert them to required=False
def optimize(expr: Expression) -> Expression:
    return expr
