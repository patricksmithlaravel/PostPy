from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")


class TestAssertion(BaseModel):
    __test__ = False  # not a pytest test class

    status_code: Optional[int] = None
    contains: Optional[List[str]] = None
    json_field_equals: Optional[Dict[str, Any]] = None


class Request(BaseModel):
    name: str
    method: str
    endpoint: str
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, Any]] = None
    body: Optional[Union[Dict[str, Any], List[Any], str]] = None
    tests: Optional[TestAssertion] = None

    @field_validator("method", mode="before")
    @classmethod
    def _check_method(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.upper()
            if value not in HTTP_METHODS:
                raise ValueError(
                    f"unsupported method {value!r} "
                    f"(expected one of {', '.join(HTTP_METHODS)})"
                )
        return value


class Collection(BaseModel):
    collection_name: str
    base_url: str
    requests: List[Request]

    @field_validator("base_url")
    @classmethod
    def _check_base_url(cls, value: str) -> str:
        # A {{variable}} is resolved from the environment at run time.
        if "{{" in value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                f"base_url must be an absolute http(s) URL or contain a "
                f"{{{{variable}}}}, got {value!r}"
            )
        return value


class Environment(BaseModel):
    variables: Dict[str, str] = Field(default_factory=dict)


class RequestHistory(BaseModel):
    method: str
    endpoint: str
    timestamp: str
    status_code: int
    response_time: float
    name: Optional[str] = None


class AssertionResult(BaseModel):
    name: str
    passed: bool
    message: str = ""
