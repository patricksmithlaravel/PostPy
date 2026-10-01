import socket
import threading
from typing import Iterator, Tuple

import pytest
import requests
from flask import Flask, Response, jsonify, redirect, request
from werkzeug.serving import make_server

from postpy import PostPy
from postpy.core.executor import RequestExecutor
from postpy.core.models import Request
from postpy.core.session import PostPySession, is_loopback

PROXY_VARS = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]


@pytest.fixture(autouse=True)
def clean_proxy_env(monkeypatch):
    for name in PROXY_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


def serve(app: Flask) -> Tuple[str, "object"]:
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_port}", server


def headers_app() -> Flask:
    app = Flask("headers")

    @app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
    @app.route("/<path:path>", methods=["GET", "POST"])
    def echo(path: str) -> Response:
        return jsonify(
            path="/" + path,
            headers={k.lower(): v for k, v in request.headers.items()},
            body=request.get_data(as_text=True),
        )

    return app


@pytest.fixture
def redirect_servers() -> Iterator[Tuple[str, str]]:
    """Two servers on different ports: ``origin`` redirects, ``target`` echoes."""
    target_url, target = serve(headers_app())
    app = Flask("origin")

    @app.route("/away", methods=["GET", "POST"])
    def away() -> Response:
        code = int(request.args.get("code", 302))
        return redirect(f"{target_url}/landing", code)

    @app.route("/same")
    def same() -> Response:
        return redirect("/landing", 302)

    @app.route("/landing")
    def landing() -> Response:
        return jsonify(headers={k.lower(): v for k, v in request.headers.items()})

    origin_url, origin = serve(app)
    yield origin_url, target_url
    origin.shutdown()
    target.shutdown()


@pytest.fixture
def fake_proxy() -> Iterator[str]:
    """An HTTP server that answers proxied requests by echoing them."""
    url, server = serve(headers_app())
    yield url
    server.shutdown()


def closed_port_url() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}"


SECRET_HEADERS = {
    "Authorization": "Bearer secret",
    "X-API-Key": "secret",
    "X-Tenant": "acme",
}


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://localhost:5001/x", True),
        ("http://api.localhost/x", True),
        ("http://127.0.0.1/x", True),
        ("http://127.5.6.7:8080/x", True),
        ("http://[::1]:5001/x", True),
        ("http://LOCALHOST/x", True),
        ("http://192.168.1.50:5001/x", False),
        ("http://10.0.0.1/x", False),
        ("https://example.com/x", False),
        ("http://localhost.example.com/x", False),
        ("http://notlocalhost/x", False),
        ("not a url", False),
    ],
)
def test_is_loopback(url, expected):
    assert is_loopback(url) is expected


def test_cross_host_redirect_drops_custom_headers(redirect_servers):
    origin, _ = redirect_servers
    response = PostPySession().get(f"{origin}/away", headers=SECRET_HEADERS)
    received = response.json()["headers"]

    assert response.json()["path"] == "/landing"
    for name in SECRET_HEADERS:
        assert name.lower() not in received
    assert "user-agent" in received
    assert "accept" in received


def test_plain_requests_would_leak_the_key(redirect_servers):
    """Documents the requests behaviour PostPySession guards against."""
    origin, _ = redirect_servers
    received = requests.get(f"{origin}/away", headers=SECRET_HEADERS).json()["headers"]
    assert received["x-api-key"] == "secret"


def test_same_host_redirect_keeps_headers(redirect_servers):
    origin, _ = redirect_servers
    received = (
        PostPySession().get(f"{origin}/same", headers=SECRET_HEADERS).json()["headers"]
    )
    assert received["authorization"] == "Bearer secret"
    assert received["x-api-key"] == "secret"
    assert received["x-tenant"] == "acme"


class BearerAuth(requests.auth.AuthBase):
    def __call__(self, r):
        r.headers["Authorization"] = "Bearer mine"
        return r


@pytest.fixture
def netrc_for_localhost(tmp_path, monkeypatch):
    path = tmp_path / "netrc"
    path.write_text("machine 127.0.0.1 login netrcuser password netrcpass\n")
    path.chmod(0o600)
    monkeypatch.setenv("NETRC", str(path))


def test_same_host_redirect_does_not_reapply_netrc(
    redirect_servers, netrc_for_localhost
):
    origin, _ = redirect_servers

    received = PostPySession().get(f"{origin}/same", auth=BearerAuth()).json()
    plain = requests.Session().get(f"{origin}/same", auth=BearerAuth()).json()

    assert received["headers"]["authorization"] == "Bearer mine"
    assert plain["headers"]["authorization"].startswith("Basic ")


def test_cross_host_307_keeps_body_and_content_type(redirect_servers):
    origin, _ = redirect_servers
    response = PostPySession().post(
        f"{origin}/away?code=307", json={"a": 1}, headers={"X-API-Key": "secret"}
    )
    body = response.json()

    assert body["body"] == '{"a": 1}'
    assert body["headers"]["content-type"] == "application/json"
    assert "x-api-key" not in body["headers"]


def test_collections_use_the_hardened_session(redirect_servers):
    origin, _ = redirect_servers
    executor = RequestExecutor(origin, {"key": "secret"})
    response = executor.execute(
        Request(
            name="Away",
            method="GET",
            endpoint="/away",
            headers={"X-API-Key": "{{key}}"},
        )
    )
    assert "x-api-key" not in response.json()["headers"]
    assert isinstance(PostPy().session, PostPySession)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_loopback_requests_bypass_environment_proxies(monkeypatch, host):
    target_url, server = serve(headers_app())
    port = target_url.rsplit(":", 1)[1]
    dead_proxy = closed_port_url()
    monkeypatch.setenv("HTTP_PROXY", dead_proxy)
    monkeypatch.setenv("HTTPS_PROXY", dead_proxy)
    try:
        url = f"http://{host}:{port}/direct"
        assert PostPy().get(url).json()["path"] == "/direct"
        with pytest.raises(requests.exceptions.ProxyError):
            requests.get(url, timeout=5)  # plain requests uses the dead proxy
    finally:
        server.shutdown()


def test_other_hosts_still_use_environment_proxies(monkeypatch, fake_proxy):
    monkeypatch.setenv("HTTP_PROXY", fake_proxy)

    body = PostPy().get("http://api.example.test/hello").json()

    assert body["path"] == "/hello"
    assert body["headers"]["host"] == "api.example.test"


def test_explicit_proxies_apply_to_loopback(fake_proxy):
    target = closed_port_url()
    body = PostPy().get(f"{target}/via-proxy", proxies={"http": fake_proxy}).json()
    assert body["path"] == "/via-proxy"

    session = PostPySession()
    session.proxies = {"http": fake_proxy}
    assert session.get(f"{target}/via-session-proxy").json()["path"] == (
        "/via-session-proxy"
    )


def test_redirect_to_loopback_skips_environment_proxy(monkeypatch, redirect_servers):
    """A proxied request redirected to loopback goes direct for the second hop."""
    _, target = redirect_servers
    app = Flask("external")

    @app.route("/start")
    def start() -> Response:
        return redirect(f"{target}/landing", 302)

    # The "external" host is reached through the proxy, which is itself an echo
    # server, so route the proxy to an app that redirects instead.
    redirecting_proxy_url, redirecting_proxy = serve(app)
    monkeypatch.setenv("HTTP_PROXY", redirecting_proxy_url)
    try:
        body = PostPy().get("http://api.example.test/start").json()
    finally:
        redirecting_proxy.shutdown()

    assert body["path"] == "/landing"
    assert body["headers"]["host"] == target.split("//")[1]
