"""
Mock server implementation.
"""

import html
import re
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlsplit

import yaml
from flask import Flask, Response, jsonify, request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    field_validator,
    model_validator,
)
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import Map, Rule

from .conditions import Condition
from .errors import format_validation_error

MOCK_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Keys that mark a response as the {status_code, body, headers} envelope form.
ENVELOPE_KEYS = frozenset({"status_code", "body", "headers"})

_PATH_PARAM = re.compile(r"\{([^{}]+)\}")
_FLASK_PARAM = re.compile(r"<(?:[^:<>]+:)?(\w+)>")
_FLASK_PARAM_NAME = re.compile(r"(?<=[<:])\w+(?=>)")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class MockConfigError(ValueError):
    """Raised when a mock server configuration cannot be loaded."""


def _is_envelope(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) <= ENVELOPE_KEYS
        and ("body" in value or "status_code" in value)
    )


def _normalize_response(data: Any) -> Any:
    """Convert either supported response layout into the envelope form.

    The documented layout nests everything under ``response``::

        response: {status_code: 404, body: {...}, headers: {...}}

    The older layout puts the body directly under ``response`` and the status
    code next to it on the endpoint. Both are accepted.
    """
    if not isinstance(data, dict):
        return data
    data = dict(data)
    response = data.get("response")
    status_code = data.pop("status_code", None)
    if _is_envelope(response):
        envelope = dict(response)
        if status_code is not None:
            envelope.setdefault("status_code", status_code)
    else:
        envelope = {"body": response}
        if status_code is not None:
            envelope["status_code"] = status_code
    data["response"] = envelope
    return data


def _substitute(value: Any, params: Dict[str, Any]) -> Any:
    """Replace ``{name}`` placeholders in strings with path parameter values.

    Works on the parsed structure, so a value containing quotes or braces can
    never change the shape of the response.
    """
    if isinstance(value, str):
        return _PLACEHOLDER.sub(
            lambda m: str(params[m.group(1)]) if m.group(1) in params else m.group(0),
            value,
        )
    if isinstance(value, list):
        return [_substitute(item, params) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, params) for key, item in value.items()}
    return value


class MockResponse(BaseModel):
    """A response returned by a mock endpoint."""

    model_config = ConfigDict(extra="forbid")

    status_code: int = Field(200, ge=100, le=599)
    body: Any = None
    headers: Dict[str, str] = Field(default_factory=dict)


class MockCondition(BaseModel):
    """An alternative response used when ``when`` is true."""

    model_config = ConfigDict(extra="forbid")

    when: str
    response: MockResponse

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        return _normalize_response(data)


class MockEndpoint(BaseModel):
    """A single mocked route."""

    model_config = ConfigDict(extra="forbid")

    path: str
    method: str = "GET"
    response: MockResponse
    conditions: List[MockCondition] = Field(default_factory=list)

    _flask_path: str = PrivateAttr("")
    _compiled: List[Tuple[Condition, MockResponse]] = PrivateAttr(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        return _normalize_response(data)

    @field_validator("path")
    @classmethod
    def _check_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError(f"path must start with '/': {value!r}")
        return value

    @field_validator("method", mode="before")
    @classmethod
    def _check_method(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.upper()
            if value not in MOCK_METHODS:
                raise ValueError(
                    f"unsupported method {value!r} "
                    f"(expected one of {', '.join(MOCK_METHODS)})"
                )
        return value

    @model_validator(mode="after")
    def _compile(self) -> "MockEndpoint":
        self._flask_path = _PATH_PARAM.sub(r"<\1>", self.path)
        try:
            Map([Rule(self._flask_path, endpoint="check")])
        except (ValueError, LookupError, SyntaxError) as exc:
            raise ValueError(f"invalid path {self.path!r}: {exc}") from None
        params = _FLASK_PARAM.findall(self._flask_path)
        self._compiled = [
            (Condition(condition.when, params), condition.response)
            for condition in self.conditions
        ]
        return self

    @property
    def flask_path(self) -> str:
        """The path in Flask's ``<param>`` routing syntax."""
        return self._flask_path

    def select_response(self, params: Dict[str, Any]) -> MockResponse:
        """Return the first matching conditional response, or the default."""
        for condition, response in self._compiled:
            if condition.matches(params):
                return response
        return self.response


class MockConfig(BaseModel):
    """Top-level mock server configuration.

    Unknown top-level keys are ignored so they can hold YAML anchors.
    """

    endpoints: List[MockEndpoint]

    @model_validator(mode="after")
    def _check_duplicates(self) -> "MockConfig":
        seen = set()
        for endpoint in self.endpoints:
            # /x/{a} and /x/{b} are the same route.
            key = (endpoint.method, _FLASK_PARAM_NAME.sub("", endpoint.flask_path))
            if key in seen:
                raise ValueError(
                    f"duplicate endpoint {endpoint.method} {endpoint.path}"
                )
            seen.add(key)
        return self


def load_mock_config(config_path: Union[str, Path]) -> MockConfig:
    """Read and validate a mock server configuration file.

    Raises:
        MockConfigError: If the file is not valid YAML or does not match the
            expected structure.
    """
    path = Path(config_path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MockConfigError(f"Cannot read {path}: {exc.strerror}") from None
    except yaml.YAMLError as exc:
        raise MockConfigError(f"{path} is not valid YAML: {exc}") from None
    if not isinstance(raw, dict):
        raise MockConfigError(f"{path} must contain a mapping with an 'endpoints' list")
    try:
        return MockConfig.model_validate(raw)
    except ValidationError as exc:
        raise MockConfigError(
            format_validation_error(exc, f"Invalid mock config {path}:")
        ) from None


def _content_type(headers: Dict[str, str]) -> str:
    for name, value in headers.items():
        if name.lower() == "content-type":
            return value.lower()
    return ""


class MockServer:
    """Mock API server for testing."""

    def __init__(self, config_path: Union[str, Path]):
        """Initialize the mock server with a configuration file.

        Args:
            config_path: Path to the YAML configuration file.

        Raises:
            MockConfigError: If the configuration is invalid.
        """
        self.config_path = str(config_path)
        self.config = load_mock_config(config_path)
        self.app = Flask(__name__)
        self.app.json.sort_keys = False  # type: ignore[attr-defined]
        # Host names accepted in the Host header; None accepts any. run() sets
        # this when binding to loopback so DNS rebinding cannot reach the server.
        self.allowed_hosts: Optional[Set[str]] = None
        self._setup_host_check()
        self._setup_routes()
        self._setup_error_handlers()

    def _make_response(self, mock: MockResponse, params: Dict[str, Any]) -> Response:
        headers = _substitute(mock.headers, params)
        content_type = _content_type(headers)
        if mock.body is None:
            response = self.app.response_class(status=mock.status_code)
        elif isinstance(mock.body, str) and content_type and "json" not in content_type:
            if "html" in content_type or "xml" in content_type:
                # Path values come straight from the URL; escape them so a
                # crafted link cannot inject markup or script into the page.
                params = {key: html.escape(str(value)) for key, value in params.items()}
            body = _substitute(mock.body, params)
            response = self.app.response_class(body, status=mock.status_code)
        else:
            response = jsonify(_substitute(mock.body, params))
            response.status_code = mock.status_code
        for name, value in headers.items():
            response.headers[name] = value
        return response

    def _setup_routes(self) -> None:
        """Register a Flask route for each configured endpoint."""

        def create_handler(endpoint: MockEndpoint) -> Callable[..., Response]:
            def handler(**params: Any) -> Response:
                return self._make_response(endpoint.select_response(params), params)

            return handler

        for index, endpoint in enumerate(self.config.endpoints):
            self.app.add_url_rule(
                endpoint.flask_path,
                endpoint=f"mock_{index}",
                methods=[endpoint.method],
                view_func=create_handler(endpoint),
            )

    def _setup_host_check(self) -> None:
        """Reject requests whose Host header is not in ``allowed_hosts``.

        A web page can point its own domain at 127.0.0.1 (DNS rebinding) and
        then read responses from a server on your machine. Its requests still
        carry the page's domain in the Host header, which this check refuses.
        """

        @self.app.before_request
        def check_host() -> Optional[Tuple[Response, int]]:
            if self.allowed_hosts is None:
                return None
            hostname = urlsplit("//" + request.host).hostname or ""
            if hostname in self.allowed_hosts or hostname.endswith(".localhost"):
                return None
            return jsonify(error="Misdirected Request"), 421

    def _setup_error_handlers(self) -> None:
        """Return JSON instead of Flask's HTML pages for routing errors."""

        @self.app.errorhandler(NotFound)
        def not_found(error: NotFound) -> Tuple[Response, int]:
            return (
                jsonify(
                    error="Not Found",
                    message=f"No mock endpoint matches {request.method} {request.path}",
                ),
                404,
            )

        @self.app.errorhandler(MethodNotAllowed)
        def method_not_allowed(error: MethodNotAllowed) -> Response:
            allowed = sorted(error.valid_methods or [])
            response = jsonify(
                error="Method Not Allowed",
                message=f"{request.method} is not allowed for {request.path}",
                allowed_methods=allowed,
            )
            response.status_code = 405
            response.headers["Allow"] = ", ".join(allowed)
            return response

    @property
    def endpoints(self) -> List[MockEndpoint]:
        """The validated endpoint definitions, in config order."""
        return self.config.endpoints

    def run(
        self, host: str = "localhost", port: int = 5000, debug: bool = False
    ) -> None:
        """Run the mock server.

        When ``host`` is a loopback address, requests must also use a loopback
        Host header. Debug mode reloads the server when the config file
        changes. Werkzeug's interactive debugger is always disabled: it allows
        code execution from the browser and the mock server has nothing to
        debug interactively.

        Args:
            host: Host to run the server on.
            port: Port to run the server on.
            debug: Whether to run in debug mode.
        """
        if host in LOOPBACK_HOSTS:
            self.allowed_hosts = set(LOOPBACK_HOSTS)
        self.app.run(
            host=host,
            port=port,
            debug=debug,
            use_debugger=False,
            use_reloader=debug,
            extra_files=[self.config_path] if debug else None,
        )

    @classmethod
    def create_config(
        cls, output_path: Union[str, Path], overwrite: bool = False
    ) -> Path:
        """Write the starter configuration file.

        Args:
            output_path: Path where the configuration file will be created.
            overwrite: Replace the file if it already exists.

        Returns:
            The path that was written.

        Raises:
            FileExistsError: If the file exists and ``overwrite`` is False.
        """
        path = Path(output_path)
        if path.exists() and not overwrite:
            raise FileExistsError(f"{path} already exists")
        template = (
            resources.files("postpy")
            .joinpath("config")
            .joinpath("mock_template.yaml")
            .read_text(encoding="utf-8")
        )
        path.write_text(template, encoding="utf-8")
        return path


__all__ = [
    "MOCK_METHODS",
    "MockCondition",
    "MockConfig",
    "MockConfigError",
    "MockEndpoint",
    "MockResponse",
    "MockServer",
    "load_mock_config",
]
