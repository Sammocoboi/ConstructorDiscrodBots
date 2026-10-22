from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from runtime.interpreter.context import Context

_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


class ExpressionError(ValueError):
    pass


def _to_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _NUMERIC_RE.fullmatch(text):
            return float(text) if "." in text else int(text)
    return None


def _coerce_pair(left: Any, right: Any) -> tuple[Any, Any]:
    left_number = _to_number(left)
    right_number = _to_number(right)
    if left_number is not None and right_number is not None:
        return left_number, right_number
    return left, right


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, Sequence, Mapping)):
        return len(value) == 0
    return False


def _contains(left: Any, right: Any) -> bool:
    if isinstance(left, str):
        return str(right) in left
    if isinstance(left, Mapping):
        return right in left
    if isinstance(left, Sequence):
        return right in left
    return False


def _compare(operator: str, left: Any, right: Any) -> bool:
    if operator in {"gt", "gte", "lt", "lte"}:
        left, right = _coerce_pair(left, right)
        try:
            if operator == "gt":
                return bool(left > right)
            if operator == "gte":
                return bool(left >= right)
            if operator == "lt":
                return bool(left < right)
            return bool(left <= right)
        except TypeError as exc:
            raise ExpressionError(
                f"cannot compare {type(left).__name__} and {type(right).__name__}"
            ) from exc
    if operator == "eq":
        return bool(_coerce_pair(left, right)[0] == _coerce_pair(left, right)[1])
    if operator == "ne":
        return bool(_coerce_pair(left, right)[0] != _coerce_pair(left, right)[1])
    if operator == "contains":
        return _contains(left, right)
    if operator == "starts_with":
        return isinstance(left, str) and left.startswith(str(right))
    if operator == "ends_with":
        return isinstance(left, str) and left.endswith(str(right))
    if operator == "in":
        return _contains(right, left)
    if operator == "is_empty":
        return _is_empty(left)
    if operator == "exists":
        return left is not None
    if operator == "matches":
        if not isinstance(left, str) or not isinstance(right, str):
            raise ExpressionError("matches expects two strings")
        try:
            return re.fullmatch(right, left) is not None
        except re.error as exc:
            raise ExpressionError(f"invalid regular expression: {exc}") from exc
    raise ExpressionError(f"unknown operator: {operator}")


def evaluate(condition: Any, ctx: Context) -> bool:
    if isinstance(condition, bool):
        return condition
    if condition is None:
        return False
    if isinstance(condition, (int, float)):
        return bool(condition)
    if isinstance(condition, str):
        return bool(ctx.resolve(condition))
    if isinstance(condition, list):
        return bool(condition)
    if not isinstance(condition, dict):
        raise ExpressionError(f"unsupported condition type: {type(condition).__name__}")

    if "jsonlogic" in condition:
        payload = condition["jsonlogic"]
        if not isinstance(payload, dict):
            raise ExpressionError("jsonlogic payload must be an object")
        return bool(_jsonlogic(payload, ctx.as_mapping()))

    if "op" in condition:
        operator = str(condition["op"])
        left = ctx.resolve_deep(condition.get("left"))
        right = ctx.resolve_deep(condition.get("right"))
        if operator == "not":
            return not evaluate(condition.get("left"), ctx)
        return _compare(operator, left, right)

    return bool(_jsonlogic(condition, ctx.as_mapping()))


def _jsonlogic(node: Any, data: Mapping[str, Any]) -> Any:
    if isinstance(node, list):
        return [_jsonlogic(item, data) for item in node]
    if not isinstance(node, dict):
        return node
    if len(node) != 1:
        raise ExpressionError("JSONLogic operation must have exactly one key")
    operator, raw_args = next(iter(node.items()))
    args = raw_args if isinstance(raw_args, list) else [raw_args]
    values = [_jsonlogic(item, data) for item in args]

    if operator == "var":
        if not values:
            return None
        path = values[0]
        default = values[1] if len(values) > 1 else None
        return _lookup(data, str(path), default)
    if operator == "missing":
        return [value for value in values if _lookup(data, str(value)) is None]
    if operator == "missing_some":
        if len(values) != 2 or not isinstance(values[1], list):
            raise ExpressionError("missing_some expects [min, [vars]]")
        missing = [value for value in values[1] if _lookup(data, str(value)) is None]
        return [] if len(values[1]) - len(missing) >= values[0] else missing
    if operator == "if":
        if len(values) < 2:
            return None
        for index in range(0, len(values) - 1, 2):
            if _truthy(values[index]):
                return values[index + 1]
        return values[-1] if len(values) % 2 == 1 else None
    if operator == "and":
        return all(_truthy(value) for value in values)
    if operator == "or":
        return next((value for value in values if _truthy(value)), False)
    if operator == "not":
        return not _truthy(values[0] if values else None)
    if operator == "cat":
        return "".join("" if value is None else str(value) for value in values)
    if operator in {"in", "contains"}:
        if len(values) != 2:
            raise ExpressionError(f"{operator} expects two arguments")
        if operator == "in":
            return _contains(values[1], values[0])
        return _contains(values[0], values[1])
    if operator in {"==", "===", "!=", "!=="}:
        if len(values) != 2:
            raise ExpressionError(f"{operator} expects two arguments")
        left, right = values
        if operator in {"==", "!="}:
            left, right = _coerce_pair(left, right)
        equal = left == right
        return not equal if operator in {"!=", "!=="} else equal
    if operator in {">", ">=", "<", "<="}:
        if len(values) != 2:
            raise ExpressionError(f"{operator} expects two arguments")
        mapping = {">": "gt", ">=": "gte", "<": "lt", "<=": "lte"}
        return _compare(mapping[operator], values[0], values[1])
    if operator in {"+", "-", "*", "/", "%"}:
        numbers = [_to_number(value) for value in values]
        if any(number is None for number in numbers):
            raise ExpressionError(f"{operator} expects numbers")
        numeric = [number for number in numbers if number is not None]
        if not numeric:
            return 0
        result: int | float = numeric[0]
        for number in numeric[1:]:
            if operator == "+":
                result += number
            elif operator == "-":
                result -= number
            elif operator == "*":
                result *= number
            elif operator == "/":
                result /= number
            else:
                result %= number
        return result
    if operator == "min":
        return min(values)
    if operator == "max":
        return max(values)
    if operator == "merge":
        merged: list[Any] = []
        for value in values:
            if isinstance(value, list):
                merged.extend(value)
            else:
                merged.append(value)
        return merged
    raise ExpressionError(f"unknown JSONLogic operator: {operator}")


def _truthy(value: Any) -> bool:
    if isinstance(value, list):
        return any(_truthy(item) for item in value)
    return bool(value)


def _lookup(data: Mapping[str, Any], path: str, default: Any = None) -> Any:
    if path == "":
        return data
    current: Any = data
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, (list, tuple)) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return default
            current = current[index]
        else:
            return default
    return current
