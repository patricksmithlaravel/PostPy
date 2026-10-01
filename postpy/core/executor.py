import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import requests
from requests.structures import CaseInsensitiveDict

from .models import AssertionResult, Request, RequestHistory, TestAssertion
from .session import PostPySession

DEFAULT_TIMEOUT = 30.0

_VARIABLE = re.compile(r"\{\{\s*([\w.-]+)\s*\}\}")
_MISSING = object()


def substitute_variables(value: Any, variables: Mapping[str, str]) -> Any:
    """Replace ``{{variable}}`` placeholders, recursing into lists and dicts.

    Placeholders with no matching variable are left unchanged.
    """
    if isinstance(value, str):
        return _VARIABLE.sub(
            lambda m: str(variables.get(m.group(1), m.group(0))), value
        )
    if isinstance(value, list):
        return [substitute_variables(item, variables) for item in value]
    if isinstance(value, dict):
        return {
            key: substitute_variables(item, variables) for key, item in value.items()
        }
    return value


def _unchanged(request: requests.PreparedRequest) -> requests.PreparedRequest:
    return request


def keep_authorization_header(
    session: requests.Session, headers: Optional[Mapping[str, Any]]
) -> Optional[Callable[[requests.PreparedRequest], requests.PreparedRequest]]:
    """Return an ``auth`` that stops ``~/.netrc`` replacing an explicit header.

    requests only reads ``~/.netrc`` when neither the request nor the session
    has ``auth``, so a no-op auth is enough to skip the lookup. Returns None
    when no ``Authorization`` header is set, so ``.netrc`` still applies to
    those requests, or when the session's own ``auth`` already skips it.
    """
    if session.auth is not None:
        return None
    merged: CaseInsensitiveDict[Any] = CaseInsensitiveDict(session.headers)
    merged.update(headers or {})
    # A None value removes a session header, as in requests.
    if merged.get("Authorization") is None:
        return None
    return _unchanged


def _lookup(data: Any, path: str) -> Any:
    """Find ``path`` in parsed JSON.

    An exact top-level key wins; otherwise the path is split on dots and list
    items are addressed by index, e.g. ``data.items.0.id``.
    """
    if isinstance(data, dict) and path in data:
        return data[path]
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.lstrip("-").isdigit():
            index = int(part)
            if not -len(current) <= index < len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


class RequestExecutor:
    def __init__(
        self,
        base_url: str,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url
        self.environment_vars = dict(environment_vars or {})
        self.timeout = timeout
        self.session = session or PostPySession()
        self.history: List[RequestHistory] = []

    def substitute(self, value: Any) -> Any:
        """Fill in ``{{variable}}`` placeholders from the environment."""
        return substitute_variables(value, self.environment_vars)

    def build_url(self, endpoint: str) -> str:
        """Join the base URL and an endpoint after variable substitution.

        An endpoint that is already an absolute URL is used as-is.
        """
        endpoint = self.substitute(endpoint)
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        base = self.substitute(self.base_url).rstrip("/")
        if endpoint and not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return f"{base}{endpoint}"

    def execute(self, request: Request) -> requests.Response:
        """Execute an HTTP request and return the response.

        Raises:
            requests.RequestException: If the request could not be completed.
        """
        url = self.build_url(request.endpoint)
        headers = self.substitute(request.headers or {})
        params = self.substitute(request.query_params or {})
        body = self.substitute(request.body)

        start_time = time.perf_counter()
        response = self.session.request(
            method=request.method,
            url=url,
            headers=headers,
            params=params,
            json=body if isinstance(body, (dict, list)) else None,
            data=body if isinstance(body, str) else None,
            timeout=self.timeout,
            auth=keep_authorization_header(self.session, headers),
        )
        response_time = time.perf_counter() - start_time

        # The endpoint is recorded before substitution so that secrets passed
        # in as variables do not end up in the history file.
        self.history.append(
            RequestHistory(
                name=request.name,
                method=request.method,
                endpoint=request.endpoint,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                status_code=response.status_code,
                response_time=response_time,
            )
        )

        return response

    def run_tests(
        self, response: requests.Response, tests: TestAssertion
    ) -> List[AssertionResult]:
        """Run test assertions against the response."""
        results: List[AssertionResult] = []

        if tests.status_code is not None:
            results.append(
                AssertionResult(
                    name="status_code",
                    passed=response.status_code == tests.status_code,
                    message=f"expected {tests.status_code}, got {response.status_code}",
                )
            )

        for text in tests.contains or []:
            found = text in response.text
            results.append(
                AssertionResult(
                    name=f"contains {text!r}",
                    passed=found,
                    message="found" if found else "not found in response body",
                )
            )

        if tests.json_field_equals:
            parsed, data = self._parse_json(response)
            for field, expected in tests.json_field_equals.items():
                name = f"json_field_equals {field!r}"
                if not parsed:
                    results.append(
                        AssertionResult(
                            name=name, passed=False, message="response is not JSON"
                        )
                    )
                    continue
                actual = _lookup(data, field)
                if actual is _MISSING:
                    message = "field not found"
                else:
                    message = f"expected {expected!r}, got {actual!r}"
                results.append(
                    AssertionResult(
                        name=name, passed=actual == expected, message=message
                    )
                )

        return results

    @staticmethod
    def _parse_json(response: requests.Response) -> Tuple[bool, Any]:
        try:
            return True, response.json()
        except ValueError:
            return False, None
