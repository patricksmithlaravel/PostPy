"""
The requests session PostPy sends everything through.
"""

import ipaddress
from typing import Any
from urllib.parse import urlparse

import requests

# Headers forwarded when a redirect leads to a different host. Everything else
# the request set, such as X-API-Key, stays with the original host. requests
# re-adds Cookie from its domain-scoped cookie jar before this check runs.
REDIRECT_SAFE_HEADERS = frozenset(
    {
        "accept",
        "accept-encoding",
        "accept-language",
        "connection",
        "content-length",
        "content-type",
        "cookie",
        "transfer-encoding",
        "user-agent",
    }
)


def is_loopback(url: str) -> bool:
    """True for ``localhost``, ``*.localhost``, 127.0.0.0/8 and ``::1``."""
    host = urlparse(url).hostname
    if not host:
        return False
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class PostPySession(requests.Session):
    """A requests Session with safer defaults for API testing.

    - On a redirect to a different host or port, only
      ``REDIRECT_SAFE_HEADERS`` are forwarded. Plain requests drops
      ``Authorization`` but re-sends custom credential headers such as
      ``X-API-Key`` to the new host. ``~/.netrc`` credentials are never added
      for the new host either. On a same-host redirect, an ``Authorization``
      header is kept rather than replaced from ``~/.netrc``.
    - Requests to loopback addresses never go through ``HTTP_PROXY`` or
      ``HTTPS_PROXY``, as in browsers. A remote proxy cannot reach your
      machine's loopback interface and would see the request's credentials.
      Proxies passed explicitly, per request or on the session, still apply.
    """

    def rebuild_auth(self, prepared_request: Any, response: Any) -> None:
        headers = prepared_request.headers
        if self.should_strip_auth(response.request.url, prepared_request.url):
            for name in list(headers):
                if name.lower() not in REDIRECT_SAFE_HEADERS:
                    del headers[name]
            # The server chose this host, so don't attach ~/.netrc credentials
            # for it. requests would, letting a redirect pick any host you have
            # a .netrc login for, over plain http if it likes.
            return
        if "Authorization" in headers:
            # Same host: keep the header. requests would otherwise re-apply
            # ~/.netrc here and replace a token the request set itself.
            return
        super().rebuild_auth(prepared_request, response)

    def rebuild_proxies(self, prepared_request: Any, proxies: Any) -> Any:
        if not self.proxies and is_loopback(prepared_request.url):
            prepared_request.headers.pop("Proxy-Authorization", None)
            return {}
        return super().rebuild_proxies(prepared_request, proxies)

    def merge_environment_settings(
        self, url: Any, proxies: Any, stream: Any, verify: Any, cert: Any
    ) -> Any:
        # Check before calling super(), which copies environment proxies into
        # the ``proxies`` dict it is given.
        explicit_proxies = bool(proxies) or bool(self.proxies)
        settings = super().merge_environment_settings(
            url, proxies, stream, verify, cert
        )
        if not explicit_proxies and is_loopback(str(url)):
            settings["proxies"] = {}
        return settings
