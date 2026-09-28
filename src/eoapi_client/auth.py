"""Bearer tokens that fetch, cache and refresh themselves.

Pass one as `auth=` to `EoApi` or a service. Services only send it to their
own URL, never to foreign asset hosts.
"""

from __future__ import annotations

import base64
import json
import math
import time
from collections.abc import Callable, Generator

import httpx

from eoapi_client._http import request


def _jwt_exp(token: str) -> float:
    """The JWT's `exp` claim, or `math.inf` for opaque tokens (then only a 401 triggers a refetch)."""
    try:
        payload = token.split(".")[1]
        return float(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["exp"])
    except (IndexError, KeyError, TypeError, ValueError):
        return math.inf


class TokenAuth(httpx.Auth):
    """Bearer token from `fetch()`, cached until 30s before its JWT `exp`; refetched once on a 401."""

    requires_request_body = True  # so a request can be replayed after a 401

    def __init__(self, fetch: Callable[[], str]) -> None:
        self._fetch = fetch
        self._token: str | None = None
        self._expires_at = 0.0

    def token(self) -> str:
        if self._token is None or time.time() >= self._expires_at - 30:
            self._token = self._fetch()
            self._expires_at = _jwt_exp(self._token)
        return self._token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.token()}"
        response = yield request
        if response.status_code == 401:
            self._token = None
            request.headers["Authorization"] = f"Bearer {self.token()}"
            yield request


def client_credentials_auth(token_url: str, client_id: str, client_secret: str, *, scope: str | None = None) -> TokenAuth:
    """OAuth2 client-credentials grant, e.g. Keycloak's `.../realms/<realm>/protocol/openid-connect/token`."""
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    if scope:
        data["scope"] = scope
    return TokenAuth(lambda: str(request("POST", token_url, data=data).json()["access_token"]))


def mock_oidc_auth(url: str, *, username: str = "eoapi-client", scopes: str = "openid") -> TokenAuth:
    """Tokens from eoapi-k8s's mock OIDC server (alukach/mock-oidc-server). Testing only."""
    data = {"username": username, "scopes": scopes}
    headers = {"Accept": "application/json"}
    return TokenAuth(lambda: str(request("POST", f"{url.rstrip('/')}/", data=data, headers=headers).json()["token"]))
