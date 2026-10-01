import pytest

from postpy.core.conditions import Condition, ConditionError


@pytest.mark.parametrize(
    "expression, values, expected",
    [
        ("{id} not in ['a', 'b']", {"id": "c"}, True),
        ("{id} not in ['a', 'b']", {"id": "a"}, False),
        ("{id} in ('a', 'b')", {"id": "b"}, True),
        ("{id} in {'a', 'b'}", {"id": "a"}, True),
        ("{id} == 'x'", {"id": "x"}, True),
        ("id != 'x'", {"id": "y"}, True),
        ("{id} == 'x' or {id} == 'y'", {"id": "y"}, True),
        ("{a} == '1' and {b} == '2'", {"a": "1", "b": "3"}, False),
        ("not {id} == 'x'", {"id": "x"}, False),
        ("{n} > 5", {"n": 7}, True),
        ("1 < {n} <= 3", {"n": 3}, True),
        ("1 < {n} <= 3", {"n": 4}, False),
        ("'ab' in {id}", {"id": "xaby"}, True),
        ("True", {}, True),
    ],
)
def test_matches(expression, values, expected):
    assert Condition(expression, values.keys()).matches(values) is expected


def test_type_mismatch_is_false():
    assert Condition("{id} > 5", ["id"]).matches({"id": "abc"}) is False


@pytest.mark.parametrize(
    "expression, message",
    [
        ("__import__('os').system('true')", "Call"),
        ("open('x')", "Call"),
        ("{id}.upper() == 'X'", "Call"),
        ("{id}[0] == 'x'", "Subscript"),
        ("{id} + 'a' == 'xa'", "BinOp"),
        ("(lambda: 1)()", "Call"),
        ("[c for c in 'ab']", "ListComp"),
        ("(x := 1)", "NamedExpr"),
        ("{id} is None", "Unsupported comparison"),
        ("{other} == 'x'", "unknown path parameter 'other'"),
        ("os == 'x'", "unknown path parameter 'os'"),
        ("{id} ==", "Invalid condition"),
    ],
)
def test_rejects_unsafe_or_invalid(expression, message):
    with pytest.raises(ConditionError, match=message):
        Condition(expression, ["id"])


def test_parameter_values_are_never_evaluated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    condition = Condition("{id} == 'x'", ["id"])
    payload = "x' or open('pwned', 'w') or '"

    assert condition.matches({"id": payload}) is False
    assert not (tmp_path / "pwned").exists()
