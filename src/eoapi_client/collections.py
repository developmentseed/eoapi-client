"""STAC collection listing.

`pystac_client.Client.get_collections()` validates each returned collection
against `matches_object_type`, which real-world STAC APIs can fail (e.g. a
collection missing a field pystac considers required). This is a plain HTTP
fetch that skips that validation.
"""

from __future__ import annotations

from typing import Any

from eoapi_client._http import get_json


def list_collections(stac_url: str, *, headers: dict[str, str] | None = None, timeout: float = 60.0) -> list[dict[str, Any]]:
    """Fetch `.../collections` and return the raw collection objects."""
    url = f"{stac_url.rstrip('/')}/collections"
    data = get_json(url, headers=headers, timeout=timeout)
    return list(data.get("collections") or [])
