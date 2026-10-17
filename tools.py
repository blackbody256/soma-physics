import ast
import math
import operator

_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {
    "sqrt": math.sqrt,
    "sin": lambda x: math.sin(math.radians(x)),
    "cos": lambda x: math.cos(math.radians(x)),
    "tan": lambda x: math.tan(math.radians(x)),
    "log10": math.log10,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id == "pi":
        return math.pi
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and len(node.args) == 1
    ):
        return _FUNCS[node.func.id](_eval(node.args[0]))
    raise ValueError("unsupported expression")


def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression exactly, for physics calculations.

    Args:
        expression: Numbers with + - * / ** and brackets, e.g. "200 / 0.05" or "0.5 * 1500 * 20**2". sin, cos and tan use degrees.

    Returns:
        The numeric result as text.
    """
    try:
        expr = expression.replace("^", "**").replace("×", "*").replace("÷", "/")
        if len(expr) > 200:
            return "error: expression too long"
        value = _eval(ast.parse(expr, mode="eval"))
        return f"{value:.6g}"
    except Exception as exc:
        return f"error: {exc}"
