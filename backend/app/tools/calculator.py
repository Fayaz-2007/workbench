"""Calculator Tool — safe arithmetic only.

Deliberately does not use `eval()`: the expression is parsed into an AST
and only a small allowlist of numeric operators/functions is evaluated.
Anything else (attribute access, calls to arbitrary names, imports,
comprehensions, ...) is rejected before it ever runs.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from app.tools.base import BaseTool, ToolResult, ToolRisk

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sum": sum,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}


class UnsafeExpressionError(ValueError):
    pass


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise UnsafeExpressionError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        args = [_eval_node(arg) for arg in node.args]
        return _FUNCTIONS[node.func.id](*args)
    if isinstance(node, ast.List):
        return [_eval_node(elt) for elt in node.elts]  # for sum()/min()/max() over literal lists
    raise UnsafeExpressionError(f"Unsupported expression: {ast.dump(node)}")


def safe_eval(expression: str) -> float:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"Could not parse expression: {exc}") from exc
    return _eval_node(tree)


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Evaluates a safe arithmetic expression (numbers, + - * / // % **, sqrt/abs/round/min/max/sum, pi, e)."
    capabilities = ["calculation"]
    risk = ToolRisk.LOW
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "required": ["expression"], "properties": {"expression": {"type": "string"}}}

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        expression = input.get("expression", "")
        try:
            result = safe_eval(expression)
        except UnsafeExpressionError as exc:
            return ToolResult(success=False, error=str(exc))
        except (ZeroDivisionError, ValueError, OverflowError) as exc:
            return ToolResult(success=False, error=f"Calculation error: {exc}")
        return ToolResult(success=True, output=result, metadata={"expression": expression})
