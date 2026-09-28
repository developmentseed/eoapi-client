"""Shared HTTP helpers."""

from __future__ import annotations

from typing import Any

import httpx


class EoApiError(Exception):
    """An eoAPI HTTP request failed."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    response = httpx.get(url, headers=headers or {}, params=params, timeout=timeout, follow_redirects=True)
    if not response.is_success:
        raise EoApiError(response.text or f"GET {url} failed", status_code=response.status_code)
    return response.json()


def post_json(
    url: str,
    *,
    json: Any,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> Any:
    response = httpx.post(url, json=json, headers=headers or {}, timeout=timeout)
    if not response.is_success:
        raise EoApiError(response.text or f"POST {url} failed", status_code=response.status_code)
    return response.json()
