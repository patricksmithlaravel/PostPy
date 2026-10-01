from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional

from requests import RequestException, Response, Session

from .executor import DEFAULT_TIMEOUT, RequestExecutor
from .models import AssertionResult, Collection, Request, RequestHistory


@dataclass
class RequestResult:
    """The outcome of running one request from a collection."""

    request: Request
    response: Optional[Response] = None
    error: Optional[str] = None
    assertions: List[AssertionResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if the request completed and every assertion passed."""
        return self.error is None and all(a.passed for a in self.assertions)


class CollectionRunner:
    """Executes the requests in a collection and checks their tests."""

    def __init__(
        self,
        collection: Collection,
        variables: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = DEFAULT_TIMEOUT,
        session: Optional[Session] = None,
    ):
        self.collection = collection
        self.executor = RequestExecutor(
            collection.base_url, variables, timeout=timeout, session=session
        )

    @property
    def requests(self) -> List[Request]:
        return self.collection.requests

    @property
    def history(self) -> List[RequestHistory]:
        return self.executor.history

    def get_request(self, name: str) -> Request:
        """Return the first request called ``name``.

        Raises:
            KeyError: If the collection has no request with that name.
        """
        for request in self.collection.requests:
            if request.name == name:
                return request
        raise KeyError(
            f"No request named {name!r} in {self.collection.collection_name!r}"
        )

    def execute(self, name: str) -> Response:
        """Send the named request and return the raw response."""
        return self.executor.execute(self.get_request(name))

    def iter_run(self, name: Optional[str] = None) -> Iterator[RequestResult]:
        """Run requests one at a time, yielding each result as it completes.

        Args:
            name: Only run requests with this name.

        Raises:
            KeyError: If ``name`` is given and no request matches it.
        """
        selected = [
            r for r in self.collection.requests if name is None or r.name == name
        ]
        if name is not None and not selected:
            self.get_request(name)  # raises KeyError with a useful message
        for request in selected:
            try:
                response = self.executor.execute(request)
            except RequestException as exc:
                yield RequestResult(request=request, error=str(exc))
                continue
            assertions = (
                self.executor.run_tests(response, request.tests)
                if request.tests
                else []
            )
            yield RequestResult(
                request=request, response=response, assertions=assertions
            )

    def run(self, name: Optional[str] = None) -> List[RequestResult]:
        """Run requests and return all results."""
        return list(self.iter_run(name))
