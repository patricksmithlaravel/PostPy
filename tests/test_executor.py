import json

import pytest
import requests

from postpy.core.executor import RequestExecutor, substitute_variables
from postpy.core.models import Request, TestAssertion


def make_response(body, status_code=200, content_type="application/json"):
    response = requests.Response()
    response.status_code = status_code
    response._content = (
        body.encode() if isinstance(body, str) else json.dumps(body).encode()
    )
    response.headers["Content-Type"] = content_type
    response.encoding = "utf-8"
    return response


def test_substitute_variables_recurses():
    value = {
        "a": "{{x}}",
        "b": ["{{ x }}-{{y}}", 3, None],
        "c": {"d": "pre {{missing}} post"},
    }
    assert substitute_variables(value, {"x": "1", "y": "2"}) == {
        "a": "1",
        "b": ["1-2", 3, None],
        "c": {"d": "pre {{missing}} post"},
    }


def test_substitution_is_single_pass():
    assert substitute_variables("{{a}}", {"a": "{{b}}", "b": "secret"}) == "{{b}}"


@pytest.mark.parametrize(
    "base_url, endpoint, expected",
    [
        ("http://h/api/", "/users", "http://h/api/users"),
        ("http://h/api", "users", "http://h/api/users"),
        ("http://h", "", "http://h"),
        ("{{base}}", "/users/{{id}}", "http://env/users/7"),
        ("http://h", "https://other.test/x", "https://other.test/x"),
    ],
)
def test_build_url(base_url, endpoint, expected):
    executor = RequestExecutor(base_url, {"base": "http://env/", "id": "7"})
    assert executor.build_url(endpoint) == expected


def test_execute_sends_substituted_request(echo_server):
    executor = RequestExecutor(echo_server, {"token": "s3cret", "id": "42", "tag": "x"})
    request = Request(
        name="Update",
        method="PUT",
        endpoint="/users/{{id}}",
        headers={"Authorization": "Bearer {{token}}"},
        query_params={"tag": "{{tag}}", "n": 2},
        body={"user": {"id": "{{id}}", "roles": ["{{tag}}"]}},
    )

    echoed = executor.execute(request).json()

    assert echoed["method"] == "PUT"
    assert echoed["path"] == "/users/42"
    assert echoed["headers"]["authorization"] == "Bearer s3cret"
    assert echoed["args"] == {"tag": ["x"], "n": ["2"]}
    assert echoed["json"] == {"user": {"id": "42", "roles": ["x"]}}

    [entry] = executor.history
    assert (entry.name, entry.method, entry.status_code) == ("Update", "PUT", 200)
    assert entry.endpoint == "/users/{{id}}"  # template, not the substituted value


def test_execute_string_and_list_bodies(echo_server):
    executor = RequestExecutor(echo_server, {"v": "1"})

    text = executor.execute(
        Request(name="t", method="POST", endpoint="/", body="v={{v}}")
    )
    assert text.json()["data"] == "v=1"

    items = executor.execute(
        Request(name="l", method="POST", endpoint="/", body=[{"v": "{{v}}"}])
    )
    assert items.json()["json"] == [{"v": "1"}]


def test_execute_times_out(echo_server):
    executor = RequestExecutor(echo_server, timeout=0.1)
    with pytest.raises(requests.Timeout):
        executor.execute(Request(name="slow", method="GET", endpoint="/slow"))
    assert executor.history == []


def test_session_keeps_cookies_between_requests(echo_server):
    executor = RequestExecutor(echo_server)
    executor.execute(Request(name="login", method="GET", endpoint="/cookie/set"))
    echoed = executor.execute(Request(name="me", method="GET", endpoint="/me")).json()
    assert echoed["cookies"] == {"session": "abc"}


def run(body, tests, **kwargs):
    return {
        a.name: (a.passed, a.message)
        for a in RequestExecutor("http://h").run_tests(
            make_response(body, **kwargs), tests
        )
    }


def test_status_code_assertion():
    assert run({}, TestAssertion(status_code=201), status_code=404) == {
        "status_code": (False, "expected 201, got 404")
    }


def test_contains_assertion_reports_each_string():
    results = run({"users": []}, TestAssertion(contains=["users", "admins"]))
    assert results == {
        "contains 'users'": (True, "found"),
        "contains 'admins'": (False, "not found in response body"),
    }


def test_json_field_equals_assertion():
    body = {
        "status": "ok",
        "a.b": "literal",
        "a": {"b": "nested"},
        "items": [{"id": 1}, {"id": 2}],
    }
    results = run(
        body,
        TestAssertion(
            json_field_equals={
                "status": "ok",
                "a.b": "literal",
                "items.1.id": 2,
                "items.-1.id": 2,
                "items.5.id": 2,
                "missing": None,
                "a": {"b": "other"},
            }
        ),
    )
    assert results == {
        "json_field_equals 'status'": (True, "expected 'ok', got 'ok'"),
        "json_field_equals 'a.b'": (True, "expected 'literal', got 'literal'"),
        "json_field_equals 'items.1.id'": (True, "expected 2, got 2"),
        "json_field_equals 'items.-1.id'": (True, "expected 2, got 2"),
        "json_field_equals 'items.5.id'": (False, "field not found"),
        "json_field_equals 'missing'": (False, "field not found"),
        "json_field_equals 'a'": (
            False,
            "expected {'b': 'other'}, got {'b': 'nested'}",
        ),
    }


def test_json_field_equals_on_array_root():
    results = run([{"id": 1}], TestAssertion(json_field_equals={"0.id": 1}))
    assert results == {"json_field_equals '0.id'": (True, "expected 1, got 1")}


def test_json_field_equals_on_non_json_response():
    results = run(
        "<html>", TestAssertion(json_field_equals={"a": 1}), content_type="text/html"
    )
    assert results == {"json_field_equals 'a'": (False, "response is not JSON")}
