"""
Safe evaluation of mock endpoint conditions.

Conditions are small boolean expressions such as
``{device_id} not in ['router1', 'switch1']``. They are parsed once, when the
config is loaded, and checked against an allow-list of syntax: literals,
path parameters, comparisons and ``and``/``or``/``not``. Path parameter values
come from the request URL, so they are only ever looked up as data and are
never spliced into the expression text.
"""

import ast
import operator
from typing import Any, Callable, Dict, Iterable, Optional

_COMPARISONS: Dict[type, Callable[[Any, Any], bool]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
}


class ConditionError(ValueError):
    """Raised when a condition expression is not valid."""


def _param_name(node: ast.AST) -> Optional[str]:
    """Return the parameter name if ``node`` refers to a path parameter.

    Both ``device_id`` and ``{device_id}`` are accepted. The latter parses as a
    one-element set display, which is how the placeholder syntax is recognised
    without rewriting the expression text.
    """
    if isinstance(node, ast.Name):
        return node.id
    if (
        isinstance(node, ast.Set)
        and len(node.elts) == 1
        and isinstance(node.elts[0], ast.Name)
    ):
        return node.elts[0].id
    return None


class Condition:
    """A compiled, validated condition expression."""

    def __init__(self, expression: str, params: Iterable[str]):
        """Parse and validate ``expression``.

        Args:
            expression: The condition source, e.g. ``"{id} == 'missing'"``.
            params: Names of the path parameters the expression may reference.

        Raises:
            ConditionError: If the expression is malformed, uses unsupported
                syntax, or references an unknown parameter.
        """
        self.expression = expression
        self._params = frozenset(params)
        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as exc:
            raise ConditionError(
                f"Invalid condition {expression!r}: {exc.msg}"
            ) from None
        self._root = tree.body
        self._check(self._root)

    def _check(self, node: ast.AST) -> None:
        name = _param_name(node)
        if name is not None:
            if name not in self._params:
                known = ", ".join(sorted(self._params)) or "none"
                raise ConditionError(
                    f"Condition {self.expression!r} references unknown path "
                    f"parameter {name!r} (available: {known})"
                )
            return
        if isinstance(node, ast.Constant):
            return
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for element in node.elts:
                self._check(element)
            return
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                self._check(value)
            return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            self._check(node.operand)
            return
        if isinstance(node, ast.Compare):
            if not all(type(op) in _COMPARISONS for op in node.ops):
                raise ConditionError(
                    f"Unsupported comparison in condition {self.expression!r}"
                )
            self._check(node.left)
            for comparator in node.comparators:
                self._check(comparator)
            return
        raise ConditionError(
            f"Unsupported syntax in condition {self.expression!r}: "
            f"{type(node).__name__} is not allowed"
        )

    def _eval(self, node: ast.AST, values: Dict[str, Any]) -> Any:
        name = _param_name(node)
        if name is not None:
            return values[name]
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return [self._eval(element, values) for element in node.elts]
        if isinstance(node, ast.BoolOp):
            results = (self._eval(value, values) for value in node.values)
            if isinstance(node.op, ast.And):
                return all(results)
            return any(results)
        if isinstance(node, ast.UnaryOp):
            return not self._eval(node.operand, values)
        if isinstance(node, ast.Compare):
            left = self._eval(node.left, values)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval(comparator, values)
                if not _COMPARISONS[type(op)](left, right):
                    return False
                left = right
            return True
        raise ConditionError(f"Unsupported syntax in condition {self.expression!r}")

    def matches(self, values: Dict[str, Any]) -> bool:
        """Evaluate the condition against the request's path parameters.

        A comparison between incompatible types (for example ``'abc' > 5``)
        evaluates to False rather than raising.
        """
        try:
            return bool(self._eval(self._root, values))
        except (TypeError, KeyError):
            return False
