"""STAC API Transactions extension client (add/delete items).

https://github.com/stac-api-extensions/transaction
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


class TransactionError(Exception):
    """A STAC API Transactions request failed."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class Transactions:
    """Create and delete STAC items via the Transactions extension."""

    def __init__(self, stac_url: str, *, headers: dict[str, str] | None = None) -> None:
        self._stac_url = stac_url.rstrip("/")
        self._headers = headers or {}

    def _url(self, collection: str, item_id: str | None = None) -> str:
        base = f"{self._stac_url}/collections/{collection}/items"
        return f"{base}/{item_id}" if item_id else base

    @staticmethod
    def _body(path_or_url: str) -> bytes:
        if urlparse(path_or_url).scheme in ("http", "https"):
            response = httpx.get(path_or_url, timeout=60.0)
            response.raise_for_status()
            return response.content
        return Path(path_or_url).read_bytes()

    def add_item(self, collection: str, path_or_url: str) -> dict[str, Any]:
        """Create an item via `POST .../items`.

        `path_or_url` may be a local file path or an `http(s)://` URL to the
        item body.
        """
        url = self._url(collection)
        with httpx.Client(headers=self._headers, timeout=60.0) as client:
            response = client.post(
                url,
                content=self._body(path_or_url),
                headers={"Content-Type": "application/geo+json"},
            )
        if response.status_code not in (200, 201):
            raise TransactionError(response.status_code, response.text or f"POST {url} failed")
        return dict(response.json())

    def delete_item(self, collection: str, item_id: str) -> None:
        """Delete an item via `DELETE .../items/{item_id}`."""
        url = self._url(collection, item_id)
        with httpx.Client(headers=self._headers, timeout=60.0) as client:
            response = client.delete(url)
        if response.status_code not in (200, 204):
            raise TransactionError(response.status_code, response.text or f"DELETE {url} failed")
