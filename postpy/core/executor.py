import json
import time
from typing import Dict, Optional, Union, Any
import requests
from datetime import datetime

from .models import Request, RequestHistory, TestAssertion

class RequestExecutor:
    def __init__(self, base_url: str, environment_vars: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip('/')
        self.environment_vars = environment_vars or {}
        self.history: List[RequestHistory] = []

    def _substitute_variables(self, value: str) -> str:
        """Replace {{variable}} placeholders with their values."""
        if not isinstance(value, str):
            return value
        
        for var_name, var_value in self.environment_vars.items():
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in value:
                value = value.replace(placeholder, str(var_value))
        return value

    def _prepare_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Prepare headers with variable substitution."""
        if not headers:
            return {}
        return {k: self._substitute_variables(v) for k, v in headers.items()}

    def _prepare_query_params(self, params: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Prepare query parameters with variable substitution."""
        if not params:
            return {}
        return {k: self._substitute_variables(v) for k, v in params.items()}

    def _prepare_body(self, body: Optional[Union[Dict[str, Any], str]]) -> Optional[Union[Dict[str, Any], str]]:
        """Prepare request body with variable substitution."""
        if isinstance(body, dict):
            return {k: self._substitute_variables(v) for k, v in body.items()}
        elif isinstance(body, str):
            return self._substitute_variables(body)
        return body

    def execute(self, request: Request) -> requests.Response:
        """Execute an HTTP request and return the response."""
        url = f"{self.base_url}{request.endpoint}"
        headers = self._prepare_headers(request.headers)
        params = self._prepare_query_params(request.query_params)
        body = self._prepare_body(request.body)

        start_time = time.time()
        response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=params,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, str) else None
        )
        response_time = time.time() - start_time

        # Record request history
        history_entry = RequestHistory(
            method=request.method,
            endpoint=request.endpoint,
            timestamp=datetime.now().isoformat(),
            status_code=response.status_code,
            response_time=response_time
        )
        self.history.append(history_entry)

        return response

    def run_tests(self, response: requests.Response, tests: TestAssertion) -> Dict[str, bool]:
        """Run test assertions against the response."""
        results = {}

        if tests.status_code is not None:
            results['status_code'] = response.status_code == tests.status_code

        if tests.contains:
            response_text = response.text
            results['contains'] = all(text in response_text for text in tests.contains)

        if tests.json_field_equals:
            try:
                response_json = response.json()
                results['json_field_equals'] = all(
                    response_json.get(key) == value
                    for key, value in tests.json_field_equals.items()
                )
            except json.JSONDecodeError:
                results['json_field_equals'] = False

        return results 