from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, HttpUrl

class TestAssertion(BaseModel):
    status_code: Optional[int] = None
    contains: Optional[List[str]] = None
    json_field_equals: Optional[Dict[str, Any]] = None

class Request(BaseModel):
    name: str
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    endpoint: str
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    body: Optional[Union[Dict[str, Any], str]] = None
    tests: Optional[TestAssertion] = None

class Collection(BaseModel):
    collection_name: str
    base_url: HttpUrl
    requests: List[Request]

class Environment(BaseModel):
    variables: Dict[str, str] = Field(default_factory=dict)

class RequestHistory(BaseModel):
    method: str
    endpoint: str
    timestamp: str
    status_code: int
    response_time: float 