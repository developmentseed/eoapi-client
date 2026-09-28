"""STAC API Transactions extension client (add/delete items).

https://github.com/stac-api-extensions/transaction
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from eoapi_client._http import EoApiError, request


class TransactionError(EoApiError):
    """A STAC API Transactions request failed."""


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
            return request("GET", path_or_url, timeout=60.0).content
        return Path(path_or_url).read_bytes()

    def add_item(self, collection: str, path_or_url: str) -> dict[str, Any]:
        """Create an item via `POST .../items`.

        `path_or_url` may be a local file path or an `http(s)://` URL to the
        item body.
        """
        response = request(
            "POST",
            self._url(collection),
            error=TransactionError,
            content=self._body(path_or_url),
            headers={**self._headers, "Content-Type": "application/geo+json"},
            timeout=60.0,
        )
        return dict(response.json())

    def delete_item(self, collection: str, item_id: str) -> None:
        """Delete an item via `DELETE .../items/{item_id}`."""
        request("DELETE", self._url(collection, item_id), error=TransactionError, headers=self._headers, timeout=60.0)
