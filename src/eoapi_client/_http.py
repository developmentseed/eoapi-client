"""Shared HTTP helpers."""

from __future__ import annotations

from typing import Any

import httpx


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


def request(method: str, url: str, *, error: type[EoApiError] = EoApiError, **kwargs: Any) -> httpx.Response:
    try:
        response = httpx.request(method, url, **kwargs)
    except httpx.TransportError as exc:
        raise EoApiConnectionError(f"{method} {url} failed: {exc}", url=url, method=method) from exc
    raise_for_response(response, error)
    return response


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    return request("GET", url, headers=headers, params=params, timeout=timeout, follow_redirects=True).json()


def post_json(
    url: str,
    *,
    json: Any,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> Any:
    return request("POST", url, json=json, headers=headers, timeout=timeout).json()
