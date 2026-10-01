import textwrap
from pathlib import Path

import pytest

from postpy.core.mock_server import MockConfigError, MockServer
from tests.conftest import EXAMPLES


@pytest.fixture
def make_client(tmp_path):
    def make(config: str):
        path = tmp_path / "mock.yaml"
        path.write_text(textwrap.dedent(config))
        return MockServer(path).app.test_client()

    return make


def test_envelope_response(make_client):
    client = make_client("""
        endpoints:
          - path: /items
            method: POST
            response:
              status_code: 201
              headers: {Location: /items/1, X-Mock: "yes"}
              body: {id: 1}
        """)
    response = client.post("/items")

    assert response.status_code == 201
    assert response.get_json() == {"id": 1}
    assert response.headers["Location"] == "/items/1"
    assert response.headers["X-Mock"] == "yes"
    assert response.content_type == "application/json"


def test_legacy_response_format(make_client):
    client = make_client("""
        endpoints:
          - path: /health
            method: GET
            response: {status: healthy}
            status_code: 202
          - path: /default
            response: {ok: true}
        """)

    response = client.get("/health")
    assert response.status_code == 202
    assert response.get_json() == {"status": "healthy"}
    assert client.get("/default").status_code == 200


def test_envelope_uses_top_level_status_code_as_fallback(make_client):
    client = make_client("""
        endpoints:
          - path: /x
            response: {body: {a: 1}}
            status_code: 418
        """)
    response = client.get("/x")
    assert response.status_code == 418
    assert response.get_json() == {"a": 1}


def test_missing_body_returns_empty_response(make_client):
    client = make_client("""
        endpoints:
          - path: /items/1
            method: DELETE
            response: {status_code: 204}
        """)
    response = client.delete("/items/1")
    assert response.status_code == 204
    assert response.data == b""


def test_string_body_with_non_json_content_type_is_sent_raw(make_client):
    client = make_client("""
        endpoints:
          - path: /hello
            response:
              headers: {Content-Type: text/plain}
              body: hello {name}
          - path: /hello/{name}
            response:
              headers: {Content-Type: text/plain}
              body: hello {name}
        """)
    assert client.get("/hello").data == b"hello {name}"
    response = client.get("/hello/sam")
    assert response.data == b"hello sam"
    assert response.content_type == "text/plain"


def test_key_order_is_preserved(make_client):
    client = make_client("""
        endpoints:
          - path: /x
            response: {body: {zebra: 1, apple: 2}}
        """)
    assert list(client.get("/x").get_json()) == ["zebra", "apple"]


def test_method_is_case_insensitive(make_client):
    client = make_client("""
        endpoints:
          - path: /x
            method: post
            response: {body: {ok: true}}
        """)
    assert client.post("/x").status_code == 200


def test_path_parameters_are_substituted_everywhere(make_client):
    client = make_client("""
        endpoints:
          - path: /devices/{device_id}/ports/{port}
            response:
              headers: {X-Device: "{device_id}"}
              body:
                id: "{device_id}"
                label: "Port {port} on {device_id}"
                tags: ["{port}", "{unknown}"]
        """)
    response = client.get("/devices/r1/ports/eth0")

    assert response.get_json() == {
        "id": "r1",
        "label": "Port eth0 on r1",
        "tags": ["eth0", "{unknown}"],
    }
    assert response.headers["X-Device"] == "r1"


@pytest.mark.parametrize(
    "value",
    ['a", "admin": true, "z": "b', 'quote"inside', "{device_id}", "back\\slash"],
)
def test_path_parameter_values_cannot_change_the_response_shape(make_client, value):
    client = make_client("""
        endpoints:
          - path: /devices/{device_id}
            response: {body: {id: "{device_id}"}}
        """)
    response = client.get(f"/devices/{value}")

    assert response.status_code == 200
    assert response.get_json() == {"id": value}


def test_typed_path_parameters(make_client):
    client = make_client("""
        endpoints:
          - path: /items/{int:item_id}
            response: {body: {id: "{item_id}"}}
            conditions:
              - when: "{item_id} > 100"
                response: {status_code: 404, body: {error: missing}}
        """)
    assert client.get("/items/7").get_json() == {"id": "7"}
    assert client.get("/items/101").status_code == 404
    assert client.get("/items/abc").status_code == 404


def test_conditions_pick_the_first_match(make_client):
    client = make_client("""
        endpoints:
          - path: /devices/{device_id}
            response: {body: {id: "{device_id}"}}
            conditions:
              - when: "{device_id} == 'locked'"
                response: {status_code: 403, body: {error: locked}}
              - when: "{device_id} not in ['r1', 'locked']"
                response: {status_code: 404, body: {error: "{device_id} not found"}}
        """)

    assert client.get("/devices/r1").get_json() == {"id": "r1"}
    assert client.get("/devices/locked").status_code == 403
    missing = client.get("/devices/zz")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "zz not found"}


def test_legacy_condition_format(make_client):
    client = make_client("""
        endpoints:
          - path: /devices/{device_id}
            response: {id: "{device_id}"}
            conditions:
              - when: "{device_id} != 'r1'"
                response: {error: Device not found}
                status_code: 404
        """)
    response = client.get("/devices/x")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Device not found"}


def test_condition_payload_in_url_is_not_executed(make_client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = make_client((EXAMPLES / "mock_config.yaml").read_text())

    response = client.get(
        "/ServicesAPI/API/V1/Device/x'+str(open('pwned','w').write('owned'))+'"
    )

    assert response.status_code == 404
    assert not (tmp_path / "pwned").exists()


def test_unknown_route_returns_json_404(make_client):
    client = make_client("endpoints: [{path: /x, response: {body: 1}}]")
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Not Found",
        "message": "No mock endpoint matches GET /nope",
    }


def test_wrong_method_returns_json_405(make_client):
    client = make_client("""
        endpoints:
          - {path: /x, method: GET, response: {body: 1}}
          - {path: /x, method: POST, response: {body: 2}}
        """)
    response = client.put("/x")

    assert response.status_code == 405
    body = response.get_json()
    assert body["error"] == "Method Not Allowed"
    assert {"GET", "POST"} <= set(body["allowed_methods"])
    assert "POST" in response.headers["Allow"]


@pytest.mark.parametrize(
    "config, message",
    [
        ("", "must contain a mapping"),
        ("- a\n- b", "must contain a mapping"),
        ("endpoints: [", "not valid YAML"),
        ("foo: 1", "endpoints: Field required"),
        ("endpoints: [{path: /x, method: FETCH}]", "unsupported method 'FETCH'"),
        ("endpoints: [{path: x}]", "path must start with '/'"),
        ("endpoints: [{path: /x, respons: {}}]", "endpoints[0].respons: Extra inputs"),
        (
            "endpoints: [{path: /x, response: {status_code: 999}}]",
            "less than or equal to 599",
        ),
        (
            "endpoints: [{path: '/x/{id}', conditions: [{when: '{idd} == 1', response: {}}]}]",
            "unknown path parameter 'idd'",
        ),
        (
            "endpoints: [{path: '/x/{id}', conditions: [{when: 'eval(id)', response: {}}]}]",
            "Call is not allowed",
        ),
        (
            "endpoints: [{path: /x}, {path: /x, method: get}]",
            "duplicate endpoint GET /x",
        ),
        (
            "endpoints: [{path: '/x/{a}'}, {path: '/x/{b}'}]",
            "duplicate endpoint GET /x/{b}",
        ),
        ("endpoints: [{path: '/x/{device-id}'}]", "invalid path '/x/{device-id}'"),
        ("endpoints: [{path: '/x/{foo:id}'}]", "converter 'foo' does not exist"),
        ("endpoints: [{path: '/x/{a}/{a}'}]", "invalid path '/x/{a}/{a}'"),
    ],
)
def test_invalid_configs_are_rejected(tmp_path, config, message):
    path = tmp_path / "bad.yaml"
    path.write_text(config)
    with pytest.raises(MockConfigError) as excinfo:
        MockServer(path)
    assert message in str(excinfo.value)


def test_unreadable_config_is_reported(tmp_path):
    with pytest.raises(MockConfigError, match="Cannot read"):
        MockServer(tmp_path)


def test_same_path_with_different_converters_is_allowed(make_client):
    client = make_client("""
        endpoints:
          - {path: "/x/{int:n}", response: {body: number}}
          - {path: "/x/{name}", response: {body: name}}
        """)
    assert client.get("/x/5").get_json() == "number"
    assert client.get("/x/abc").get_json() == "name"


def test_top_level_keys_can_hold_yaml_anchors(make_client):
    client = make_client("""
        x-ok: &ok {status_code: 200, body: {ok: true}}
        endpoints:
          - {path: /a, response: *ok}
        """)
    assert client.get("/a").get_json() == {"ok": True}


def test_example_config_loads():
    server = MockServer(EXAMPLES / "mock_config.yaml")
    assert len(server.endpoints) == 11


def test_create_config_writes_a_working_template(tmp_path):
    path = MockServer.create_config(tmp_path / "mock.yaml")
    client = MockServer(path).app.test_client()

    assert client.get("/api/v1/health").get_json()["status"] == "healthy"
    assert client.post("/api/v1/users").status_code == 201
    assert client.get("/api/v1/users/1").get_json()["id"] == "1"
    assert client.get("/api/v1/users/99").status_code == 404


def test_create_config_does_not_overwrite_by_default(tmp_path):
    path = tmp_path / "mock.yaml"
    path.write_text("keep me")

    with pytest.raises(FileExistsError):
        MockServer.create_config(path)
    assert path.read_text() == "keep me"

    MockServer.create_config(path, overwrite=True)
    assert "endpoints:" in path.read_text()


def test_run_never_enables_the_interactive_debugger(monkeypatch):
    server = MockServer(EXAMPLES / "mock_config.yaml")
    calls = []
    monkeypatch.setattr(server.app, "run", lambda **kwargs: calls.append(kwargs))

    server.run(host="127.0.0.1", port=1234, debug=True)
    server.run()

    assert calls[0]["use_debugger"] is False
    assert calls[0]["use_reloader"] is True
    assert calls[0]["extra_files"] == [str(Path(EXAMPLES / "mock_config.yaml"))]
    assert calls[1]["use_debugger"] is False
    assert calls[1]["use_reloader"] is False
