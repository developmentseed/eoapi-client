"""STAC API Transactions extension client (add/delete items).

https://github.com/stac-api-extensions/transaction
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from eoapi_client._http import EoApiError, Service, request


class TransactionError(EoApiError):
    """A STAC API Transactions request failed."""


class Transactions(Service):
    """Create and delete STAC items via the Transactions extension."""

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
        response = self._request(
            "POST",
            f"/collections/{collection}/items",
            error=TransactionError,
            content=self._body(path_or_url),
            headers={"Content-Type": "application/geo+json"},
        )
        return dict(response.json())

    def delete_item(self, collection: str, item_id: str) -> None:
        """Delete an item via `DELETE .../items/{item_id}`."""
        self._request("DELETE", f"/collections/{collection}/items/{item_id}", error=TransactionError)
