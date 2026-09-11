"""Safe formula engine used by Health Composer.

This intentionally never calls eval/exec. Expressions are parsed to AST and only a small
allow-list is interpreted.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any, Callable, Mapping

class ComposerError(ValueError):
    """Raised when a composer expression is invalid or unsafe."""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def _normalize(value: float, low: float, high: float) -> float:
    if high == low:return 0.0
    return _clamp((value-low)/(high-low), 0.0, 1.0)
def _coalesce(*values: Any) -> Any:return next((v for v in values if v is not None), None)
def _ratio(a: float, b: float) -> float | None:return None if b == 0 else a/b

_ALLOWED_FUNCS={"clamp":_clamp,"normalize":_normalize,"coalesce":_coalesce,"ratio":_ratio,"abs":abs,"min":min,"max":max,"round":round}
_BINARY={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow}
_UNARY={ast.UAdd:operator.pos,ast.USub:operator.neg,ast.Not:operator.not_}
_COMPARE={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge}

class SafeFormula:
    """Compile and execute a restricted arithmetic/boolean expression."""
    def __init__(self,expression:str,*,max_nodes:int=120)->None:
        if not expression or len(expression)>4096:raise ComposerError("Formula is empty or too long")
        try:self._tree=ast.parse(expression,mode="eval")
        except SyntaxError as err:raise ComposerError(f"Invalid formula: {err.msg}") from err
        nodes=list(ast.walk(self._tree))
        if len(nodes)>max_nodes:raise ComposerError("Formula is too complex")
        forbidden=(ast.Attribute,ast.Subscript,ast.Lambda,ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp,ast.Await,ast.NamedExpr)
        if any(isinstance(n,forbidden) for n in nodes):raise ComposerError("Unsupported or unsafe formula construct")
    def evaluate(self,variables:Mapping[str,Any])->float|int|bool|None:
        result=self._node(self._tree.body,variables)
        if isinstance(result,float) and not math.isfinite(result):raise ComposerError("Formula produced NaN or infinity")
        if result is not None and not isinstance(result,(int,float,bool)):raise ComposerError("Formula produced unsupported result")
        return result
    def _node(self,node:ast.AST,variables:Mapping[str,Any])->Any:
        if isinstance(node,ast.Constant):
            if node.value is None or isinstance(node.value,(int,float,bool)):return node.value
            raise ComposerError("Only numeric, boolean and null constants are allowed")
        if isinstance(node,ast.Name):
            if node.id not in variables:raise ComposerError(f"Unknown input: {node.id}")
            return variables[node.id]
        if isinstance(node,ast.BinOp):
            fn=_BINARY.get(type(node.op))
            if fn is None:raise ComposerError("Operator not allowed")
            left=self._node(node.left,variables);right=self._node(node.right,variables)
            if left is None or right is None:return None
            try:return fn(left,right)
            except (ArithmeticError,TypeError) as err:raise ComposerError(str(err)) from err
        if isinstance(node,ast.UnaryOp):
            fn=_UNARY.get(type(node.op))
            if fn is None:raise ComposerError("Unary operator not allowed")
            value=self._node(node.operand,variables)
            if value is None and not isinstance(node.op,ast.Not):return None
            return fn(value)
        if isinstance(node,ast.BoolOp):
            vals=[bool(self._node(v,variables)) for v in node.values]
            return all(vals) if isinstance(node.op,ast.And) else any(vals)
        if isinstance(node,ast.Compare):
            left=self._node(node.left,variables)
            for op_node,comp in zip(node.ops,node.comparators,strict=True):
                right=self._node(comp,variables);fn=_COMPARE.get(type(op_node))
                if fn is None:raise ComposerError("Comparison not allowed")
                if not fn(left,right):return False
                left=right
            return True
        if isinstance(node,ast.IfExp):return self._node(node.body if self._node(node.test,variables) else node.orelse,variables)
        if isinstance(node,ast.Call):
            if not isinstance(node.func,ast.Name) or node.func.id not in _ALLOWED_FUNCS:raise ComposerError("Function not allowed")
            if node.keywords:raise ComposerError("Keyword arguments are not allowed")
            args=[self._node(a,variables) for a in node.args]
            try:return _ALLOWED_FUNCS[node.func.id](*args)
            except (ArithmeticError,TypeError,ValueError) as err:raise ComposerError(str(err)) from err
        raise ComposerError(f"Unsupported expression node: {type(node).__name__}")
