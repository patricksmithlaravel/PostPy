import socket
import subprocess
import sys

import pytest
from click.testing import CliRunner

from postpy import __version__
from postpy.cli import cli
from postpy.core.mock_server import MockServer
from tests.conftest import EXAMPLES


@pytest.fixture
def invoke():
    def invoke(*args):
        return CliRunner().invoke(cli, [str(a) for a in args], catch_exceptions=False)

    return invoke


def closed_port_url() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def test_version(invoke):
    result = invoke("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_lists_every_command(invoke):
    output = invoke("--help").output
    for command in ("run-collection", "show-collection", "show-history", "mock"):
        assert command in output


def test_python_dash_m():
    result = subprocess.run(
        [sys.executable, "-m", "postpy", "--version"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_run_collection_passes(invoke, echo_server, write_collection):
    path = write_collection(
        echo_server,
        [
            {
                "name": "Get Users",
                "method": "GET",
                "endpoint": "/users",
                "tests": {"status_code": 200, "json_field_equals": {"path": "/users"}},
            }
        ],
    )
    result = invoke("run-collection", path)

    assert result.exit_code == 0, result.output
    assert "PASS  Get Users  GET /users  -> 200" in result.output
    assert "1 passed, 0 failed" in result.output


def test_run_collection_fails_on_assertion(invoke, echo_server, write_collection):
    path = write_collection(
        echo_server,
        [
            {"name": "Ok", "method": "GET", "endpoint": "/"},
            {
                "name": "Bad",
                "method": "GET",
                "endpoint": "/status/500",
                "tests": {"status_code": 200},
            },
        ],
    )
    result = invoke("run-collection", path)

    assert result.exit_code == 1
    assert "FAIL  Bad" in result.output
    assert "expected 200, got 500" in result.output
    assert "1 passed, 1 failed" in result.output


def test_run_collection_reports_connection_errors(invoke, write_collection):
    path = write_collection(
        closed_port_url(), [{"name": "Down", "method": "GET", "endpoint": "/"}]
    )
    result = invoke("run-collection", path, "--timeout", "2")

    assert result.exit_code == 1
    assert "FAIL  Down" in result.output
    assert "error:" in result.output


def test_run_collection_with_env_file(invoke, echo_server, write_collection, tmp_path):
    env = tmp_path / "test.env"
    env.write_text(f"base={echo_server}\ntoken=abc\n")
    path = write_collection(
        "{{base}}",
        [
            {
                "name": "Auth",
                "method": "GET",
                "endpoint": "/me",
                "headers": {"Authorization": "Bearer {{token}}"},
                "tests": {"json_field_equals": {"headers.authorization": "Bearer abc"}},
            }
        ],
    )
    result = invoke("run-collection", path, "--env-file", env)

    assert result.exit_code == 0, result.output


def test_run_collection_single_request(invoke, echo_server, write_collection):
    path = write_collection(
        echo_server,
        [
            {"name": "One", "method": "GET", "endpoint": "/one"},
            {"name": "Two", "method": "GET", "endpoint": "/two"},
        ],
    )

    result = invoke("run-collection", path, "-r", "Two")
    assert result.exit_code == 0
    assert "Two" in result.output and "One" not in result.output

    result = invoke("run-collection", path, "-r", "Three")
    assert result.exit_code == 1
    assert "No request named 'Three'" in result.output


def test_quiet_hides_bodies(invoke, echo_server, write_collection):
    path = write_collection(
        echo_server, [{"name": "A", "method": "GET", "endpoint": "/body-marker"}]
    )

    assert '"/body-marker"' in invoke("run-collection", path).output
    assert '"/body-marker"' not in invoke("run-collection", path, "-q").output


def test_markup_in_responses_and_names_is_printed_literally(
    invoke, echo_server, write_collection
):
    path = write_collection(
        echo_server,
        [{"name": "[bold]Name[/bold]", "method": "GET", "endpoint": "/text"}],
        name="[red]Collection",
    )

    result = invoke("run-collection", path)
    assert result.exit_code == 0, result.output
    assert "closing [/posts] and [bold]markup[/bold]" in result.output
    assert "[bold]Name[/bold]" in result.output

    result = invoke("show-collection", path)
    assert result.exit_code == 0, result.output
    assert "[red]Collection" in result.output


def test_invalid_collection(invoke, tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"collection_name": "C", "base_url": "nope", "requests": [{}]}')

    result = invoke("run-collection", path)

    assert result.exit_code == 1
    assert "Invalid collection" in result.output
    assert "base_url: base_url must be an absolute http(s) URL" in result.output
    assert "requests[0].name: Field required" in result.output


def test_missing_collection(invoke, tmp_path):
    for command in ("run-collection", "show-collection"):
        result = invoke(command, tmp_path / "missing.json")
        assert result.exit_code == 1
        assert "Collection file not found" in result.output


def test_show_collection(invoke):
    result = invoke("show-collection", EXAMPLES / "api_tests.json")
    assert result.exit_code == 0
    assert "Example API Tests" in result.output
    assert "Create Post" in result.output


def test_show_history(invoke, echo_server, write_collection):
    path = write_collection(
        echo_server, [{"name": "Zebra", "method": "GET", "endpoint": "/h"}]
    )

    assert "No request history available" in invoke("show-history", path).output

    invoke("run-collection", path, "-q")
    invoke("run-collection", path, "-q")
    output = invoke("show-history", path).output
    assert output.count("Zebra") == 2
    assert invoke("show-history", path, "-n", "1").output.count("Zebra") == 1


def test_example_collection_against_example_mock_server(
    invoke, example_mock_server, tmp_path
):
    env = tmp_path / "mock.env"
    env.write_text(
        (EXAMPLES / "mock.env")
        .read_text()
        .replace("http://127.0.0.1:5001", example_mock_server)
    )

    result = invoke("run-collection", EXAMPLES / "mock_api_tests.json", "-e", env, "-q")

    assert result.exit_code == 0, result.output
    assert "8 passed, 0 failed" in result.output


def test_mock_init(invoke, tmp_path):
    path = tmp_path / "mock.yaml"

    result = invoke("mock", "init", path)
    assert result.exit_code == 0
    assert "endpoints:" in path.read_text()

    path.write_text("mine")
    result = invoke("mock", "init", path)
    assert result.exit_code == 1
    assert "already exists. Use --force" in result.output
    assert path.read_text() == "mine"

    assert invoke("mock", "init", path, "--force").exit_code == 0
    assert "endpoints:" in path.read_text()


def test_mock_run_rejects_invalid_config(invoke, tmp_path, monkeypatch):
    monkeypatch.setattr(
        MockServer, "run", lambda *a, **kw: pytest.fail("server started")
    )
    path = tmp_path / "bad.yaml"
    path.write_text("endpoints: [{path: /x, method: FETCH}]")

    result = invoke("mock", "run", path)

    assert result.exit_code == 1
    assert "endpoints[0].method: unsupported method 'FETCH'" in result.output


def test_mock_run_starts_server(invoke, monkeypatch):
    calls = []
    monkeypatch.setattr(MockServer, "run", lambda self, **kw: calls.append(kw))

    result = invoke("mock", "run", EXAMPLES / "mock_config.yaml", "--port", "5050")

    assert result.exit_code == 0, result.output
    assert calls == [{"host": "localhost", "port": 5050, "debug": False}]
    assert "/ServicesAPI/API/V1/Device/{device_id}" in result.output
    assert "Warning" not in result.output


def test_mock_run_warns_when_exposed(invoke, monkeypatch):
    monkeypatch.setattr(MockServer, "run", lambda self, **kw: None)
    result = invoke("mock", "run", EXAMPLES / "mock_config.yaml", "--host", "0.0.0.0")
    assert "reachable from other machines" in result.output
