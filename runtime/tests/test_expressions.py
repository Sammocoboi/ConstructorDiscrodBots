from __future__ import annotations

import pytest

from runtime.interpreter.context import Context
from runtime.interpreter.expressions import ExpressionError, evaluate


def test_operator_equality_and_numbers():
    ctx = Context(user={"id": "42", "age": 20}, variables={"score": 10})
    assert evaluate({"op": "eq", "left": "{user.id}", "right": "42"}, ctx)
    assert evaluate({"op": "gt", "left": "{variables.score}", "right": "9"}, ctx)
    assert evaluate({"op": "gte", "left": "{user.age}", "right": 20}, ctx)
    assert evaluate({"op": "ne", "left": "a", "right": "b"}, ctx)


def test_operator_contains_and_empty():
    ctx = Context(message={"content": "hello world"})
    assert evaluate({"op": "contains", "left": "{message.content}", "right": "world"}, ctx)
    assert evaluate({"op": "starts_with", "left": "{message.content}", "right": "hello"}, ctx)
    assert evaluate({"op": "is_empty", "left": "{args.missing}"}, ctx)
    assert evaluate({"op": "exists", "left": "{user.name}"}, ctx) is False


def test_jsonlogic():
    ctx = Context(user={"id": "42"}, args={"amount": 5})
    assert evaluate({"==": [{"var": "user.id"}, "42"]}, ctx)
    assert evaluate(
        {"and": [{">": [{"var": "args.amount"}, 1]}, {"<": [{"var": "args.amount"}, 10]}]},
        ctx,
    )
    assert evaluate({"jsonlogic": {"in": ["a", ["a", "b"]]}}, ctx)


def test_string_condition_is_resolved():
    ctx = Context(user={"name": "Shuhrat"})
    assert evaluate("{user.name}", ctx)
    assert evaluate("{user.missing}", ctx) is False


def test_invalid_expression_raises():
    with pytest.raises(ExpressionError):
        evaluate({"op": "unknown", "left": 1, "right": 2}, Context())
    with pytest.raises(ExpressionError):
        evaluate({"op": "matches", "left": "[", "right": "["}, Context())
    with pytest.raises(ExpressionError):
        evaluate({"nonsense": 1}, Context())
