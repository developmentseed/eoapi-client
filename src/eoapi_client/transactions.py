"""STAC API Transactions extension client (item and collection writes).

https://github.com/stac-api-extensions/transaction
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from itertools import islice
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from eoapi_client._http import DEFAULT_TIMEOUT, EoApiError, Service, request

MERGE_PATCH = {"Content-Type": "application/merge-patch+json"}


class TransactionError(EoApiError):
    """A STAC API Transactions request failed."""


def _as_json(obj: Any) -> dict[str, Any]:
    """A dict as-is, a pystac object via `.to_dict()`, an `http(s)://` URL (fetched without auth), or a local path."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return dict(obj.to_dict())
    if urlparse(str(obj)).scheme in ("http", "https"):
        return dict(request("GET", str(obj), timeout=DEFAULT_TIMEOUT).json())
    return dict(json.loads(Path(obj).read_text()))


class Transactions(Service):
    """Create, update and delete STAC items and collections via the Transactions extension.

    Items and collections may be given as a dict, a pystac object, a local
    file path or an `http(s)://` URL.
    """

    def _write(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        return dict(self._request(method, path, error=TransactionError, **kwargs).json())

    def add_item(self, collection: str, item: Any) -> dict[str, Any]:
        """Create an item via `POST /collections/{collection}/items`."""
        return self._write("POST", f"/collections/{collection}/items", json=_as_json(item))

    def update_item(self, collection: str, item: Any) -> dict[str, Any]:
        """Replace an item via `PUT /collections/{collection}/items/{item["id"]}`."""
        body = _as_json(item)
        return self._write("PUT", f"/collections/{collection}/items/{body['id']}", json=body)

    def patch_item(self, collection: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Update an item with a JSON merge patch (RFC 7396)."""
        path = f"/collections/{collection}/items/{item_id}"
        return self._write("PATCH", path, content=json.dumps(patch), headers=MERGE_PATCH)

    def delete_item(self, collection: str, item_id: str) -> None:
        """Delete an item via `DELETE .../items/{item_id}`."""
        self._request("DELETE", f"/collections/{collection}/items/{item_id}", error=TransactionError)

    def bulk_add_items(
        self, collection: str, items: Iterable[Any], *, method: str = "insert", chunk_size: int = 500
    ) -> None:
        """Insert (or, with `method="upsert"`, upsert) items via `POST .../bulk_items`, `chunk_size` per request.

        Each chunk is its own request: if one fails, earlier chunks stay committed.
        """
        it = iter(items)
        while chunk := [_as_json(item) for item in islice(it, chunk_size)]:
            body = {"items": {item["id"]: item for item in chunk}, "method": method}
            self._request("POST", f"/collections/{collection}/bulk_items", error=TransactionError, json=body)

    def add_collection(self, collection: Any) -> dict[str, Any]:
        """Create a collection via `POST /collections`."""
        return self._write("POST", "/collections", json=_as_json(collection))

    def update_collection(self, collection: Any) -> dict[str, Any]:
        """Replace a collection via `PUT /collections/{collection["id"]}`."""
        body = _as_json(collection)
        return self._write("PUT", f"/collections/{body['id']}", json=body)

    def patch_collection(self, collection_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Update a collection with a JSON merge patch (RFC 7396)."""
        return self._write("PATCH", f"/collections/{collection_id}", content=json.dumps(patch), headers=MERGE_PATCH)

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection via `DELETE /collections/{collection_id}` (pgstac also deletes its items)."""
        self._request("DELETE", f"/collections/{collection_id}", error=TransactionError)
