"""
High-level Python API.
"""

import os
from typing import Any, Mapping, Optional, Union

import requests

from .core.executor import DEFAULT_TIMEOUT, substitute_variables
from .core.loader import CollectionLoader
from .core.runner import CollectionRunner

EnvironmentSource = Union[Mapping[str, str], str, "os.PathLike[str]"]


class PostPy:
    """Send requests and run collections with shared variables and cookies.

    Example::

        client = PostPy(environment=".env")
        client.get("https://api.example.com/users").json()

        collection = client.load_collection("api_tests.json")
        collection.execute("Get Users")
    """

    def __init__(
        self,
        environment: Optional[EnvironmentSource] = None,
        timeout: Optional[float] = DEFAULT_TIMEOUT,
    ):
        """
        Args:
            environment: Variables for ``{{name}}`` placeholders, either a
                mapping or the path to a .env file.
            timeout: Seconds to wait for each response; None waits forever.
        """
        if environment is None:
            self.variables = {}
        elif isinstance(environment, (str, os.PathLike)):
            self.variables = CollectionLoader.load_environment(environment).variables
        else:
            self.variables = dict(environment)
        self.timeout = timeout
        self.session = requests.Session()

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Send a request; ``{{name}}`` placeholders in ``url`` are filled in.

        Keyword arguments are passed to :meth:`requests.Session.request`.
        """
        url = substitute_variables(url, self.variables)
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method.upper(), url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("OPTIONS", url, **kwargs)

    def load_collection(self, path: Union[str, "os.PathLike[str]"]) -> CollectionRunner:
        """Load a JSON or YAML collection that shares this client's session."""
        collection = CollectionLoader.load_collection(path)
        return CollectionRunner(
            collection, self.variables, timeout=self.timeout, session=self.session
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "PostPy":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
