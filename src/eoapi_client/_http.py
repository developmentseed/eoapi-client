"""Shared HTTP helpers."""

from __future__ import annotations

from importlib.metadata import version
from typing import Any, Self

import httpx

DEFAULT_TIMEOUT = 60.0


class EoApiError(Exception):
    """An eoAPI HTTP request failed."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        url: str | None = None,
        method: str | None = None,
        body: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.method = method
        self.body = body
        super().__init__(message)


class EoApiConnectionError(EoApiError):
    """An eoAPI request failed before a response was received (DNS, connection, timeout)."""


def raise_for_response(response: httpx.Response, error: type[EoApiError] = EoApiError) -> None:
    if response.is_success:
        return
    response.read()
    method, url = response.request.method, str(response.request.url)
    raise error(
        f"{method} {url} → {response.status_code}: {response.text[:500]}",
        status_code=response.status_code,
        url=url,
        method=method,
        body=response.text,
    )


def new_client(timeout: float | httpx.Timeout = DEFAULT_TIMEOUT) -> httpx.Client:
    """An `httpx.Client` with eoapi-client's defaults: redirects, connection retries, User-Agent."""
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": f"eoapi-client/{version('eoapi-client')}"},
        transport=httpx.HTTPTransport(retries=2),
    )


def request(
    method: str,
    url: str,
    *,
    client: httpx.Client | None = None,
    error: type[EoApiError] = EoApiError,
    **kwargs: Any,
) -> httpx.Response:
    try:
        response = (client or httpx).request(method, url, **kwargs)
    except httpx.TransportError as exc:
        raise EoApiConnectionError(f"{method} {url} failed: {exc}", url=url, method=method) from exc
    raise_for_response(response, error)
    return response


class ClientOwner:
    """Holds an `httpx.Client`, closing it on `close()` only if it created it."""

    def __init__(self, client: httpx.Client | None, timeout: float) -> None:
        self._client = client or new_client(timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class Service(ClientOwner):
    """Base for one eoAPI service. Headers and auth are sent per request, not as client defaults."""

    def __init__(
        self,
        url: str,
        *,
        client: httpx.Client | None = None,
        headers: dict[str, str] | None = None,
        auth: httpx.Auth | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(client, timeout)
        self._url = url.rstrip("/")
        self._headers = headers or {}
        self._auth = auth

    def _request(self, method: str, path: str, *, error: type[EoApiError] = EoApiError, **kwargs: Any) -> httpx.Response:
        headers = {**self._headers, **kwargs.pop("headers", {})}
        url = f"{self._url}{path}"
        return request(method, url, client=self._client, error=error, headers=headers, auth=self._auth, **kwargs)
