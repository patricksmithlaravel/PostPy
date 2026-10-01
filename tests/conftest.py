import base64
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List

import pytest
from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

from postpy.core.mock_server import MockServer

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@pytest.fixture(autouse=True)
def postpy_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep request history out of the real home directory."""
    home = tmp_path / "postpy-home"
    monkeypatch.setenv("POSTPY_HOME", str(home))
    return home


@pytest.fixture
def netrc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Give requests .netrc credentials for 127.0.0.1.

    Returns the ``Authorization`` header those credentials produce.
    """
    path = tmp_path / "netrc"
    path.write_text("machine 127.0.0.1 login netrcuser password netrcpass\n")
    monkeypatch.setenv("NETRC", str(path))
    return "Basic " + base64.b64encode(b"netrcuser:netrcpass").decode()


def _serve(app: Flask) -> Iterator[str]:
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def _echo_app() -> Flask:
    app = Flask("echo")

    @app.route("/status/<int:code>", methods=METHODS)
    def status(code: int) -> Any:
        return jsonify(code=code), code

    @app.route("/cookie/set")
    def set_cookie() -> Response:
        response = jsonify(ok=True)
        response.set_cookie("session", "abc")
        return response

    @app.route("/text")
    def text() -> Response:
        return Response(
            "closing [/posts] and [bold]markup[/bold]", mimetype="text/plain"
        )

    @app.route("/escape")
    def escape() -> Response:
        return Response(
            "ok\x1b]0;title\x07\x1b]52;c;cHduZWQ=\x07\x1b[1A\x9b2K\r\nend",
            mimetype="text/plain",
        )

    @app.route("/escape-json")
    def escape_json() -> Response:
        return jsonify(value="a\x1b[31mred\x9b2K")

    @app.route("/list")
    def as_list() -> Response:
        return jsonify([{"id": 1}, {"id": 2}])

    @app.route("/slow")
    def slow() -> Response:
        time.sleep(1)
        return jsonify(ok=True)

    @app.route("/", defaults={"path": ""}, methods=METHODS)
    @app.route("/<path:path>", methods=METHODS)
    def echo(path: str) -> Response:
        return jsonify(
            method=request.method,
            path="/" + path,
            args=request.args.to_dict(flat=False),
            headers={k.lower(): v for k, v in request.headers.items()},
            json=request.get_json(silent=True),
            data=request.get_data(as_text=True),
            cookies=request.cookies,
        )

    return app


@pytest.fixture
def echo_server() -> Iterator[str]:
    """A live HTTP server that echoes each request back as JSON."""
    yield from _serve(_echo_app())


@pytest.fixture
def example_mock_server() -> Iterator[str]:
    """The example mock config served over real HTTP."""
    yield from _serve(MockServer(EXAMPLES / "mock_config.yaml").app)


@pytest.fixture
def write_collection(tmp_path: Path) -> Callable[..., Path]:
    def write(
        base_url: str, requests: List[Dict[str, Any]], name: str = "Tests"
    ) -> Path:
        path = tmp_path / "collection.json"
        path.write_text(
            json.dumps(
                {"collection_name": name, "base_url": base_url, "requests": requests}
            )
        )
        return path

    return write
