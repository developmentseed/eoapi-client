"""STAC reads: collections, items, asset downloads."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from eoapi_client._http import (
    DEFAULT_TIMEOUT,
    EoApiConnectionError,
    EoApiError,
    Service,
    new_client,
    raise_for_response,
    request,
)


class AssetNotFoundError(EoApiError):
    """The requested asset key doesn't exist on the item."""


class UnsupportedAssetSchemeError(EoApiError):
    """The asset href uses a scheme that can't be fetched over HTTP."""


class Stac(Service):
    """Read collections and items from a STAC API and download assets."""

    def _pages(self, path: str, key: str, params: dict[str, Any] | None) -> Iterator[dict[str, Any]]:
        """Yield `data[key]` entries across pages, following `rel="next"` links."""
        url: str | None = f"{self._url}{path}"
        seen: set[str] = set()
        while url and url not in seen:
            seen.add(url)
            data = request("GET", url, client=self._client, headers=self._headers, params=params).json()
            yield from data.get(key) or []
            url = next((link["href"] for link in data.get("links") or [] if link.get("rel") == "next"), None)
            params = None  # the next href already carries them; `{}` would make httpx drop its query

    def iter_collections(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Yield the raw collection objects of `.../collections`, across all pages.

        Plain HTTP, so it tolerates collections that fail `pystac_client`'s
        stricter validation (`matches_object_type`). Extra keyword arguments
        (`limit`, `q`, `bbox`, `datetime`, `filter`, `sortby`, ...) are passed
        through as query parameters; use `**{"filter-lang": ...}` for names
        that aren't valid identifiers.
        """
        return self._pages("/collections", "collections", params)

    def collections(self, **params: Any) -> list[dict[str, Any]]:
        """`list(iter_collections(**params))`."""
        return list(self.iter_collections(**params))

    def iter_items(self, collection: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Yield a collection's items across all pages; params as for `iter_collections`."""
        return self._pages(f"/collections/{collection}/items", "features", params)

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/collections/{collection_id}").json())

    def get_item(self, collection: str, item_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/collections/{collection}/items/{item_id}").json())

    def download_asset(self, collection: str, item_id: str, asset_key: str, dest: Path) -> Path:
        """Resolve an item's asset href and stream it to `dest`.

        Auth headers are only sent to the asset href when it shares the STAC
        API's host — asset hrefs commonly point at a different host (object
        storage, a CDN) that shouldn't receive the STAC API's bearer token.
        Foreign hosts are fetched with a separate plain client, so a shared
        client's default headers don't leak either.
        """
        asset = (self.get_item(collection, item_id).get("assets") or {}).get(asset_key)
        if asset is None:
            raise AssetNotFoundError(f"Asset {asset_key!r} not found on item {item_id!r}")
        href = str(asset["href"])
        parsed_href = urlparse(href)
        if parsed_href.scheme not in ("http", "https"):
            raise UnsupportedAssetSchemeError(
                f"Asset {asset_key!r} uses an unsupported scheme ({parsed_href.scheme!r}) — "
                "likely only reachable from inside the platform (e.g. a shared filesystem "
                "mount) and cannot be downloaded directly."
            )
        same_host = parsed_href.netloc == urlparse(self._url).netloc
        client = self._client if same_host else new_client(self._client.timeout)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with client.stream("GET", href, headers=self._headers if same_host else {}) as response:
                raise_for_response(response)
                with dest.open("wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        except httpx.TransportError as exc:
            raise EoApiConnectionError(f"GET {href} failed: {exc}", url=href, method="GET") from exc
        finally:
            if not same_host:
                client.close()
        return dest


def list_collections(
    stac_url: str, *, headers: dict[str, str] | None = None, timeout: float = DEFAULT_TIMEOUT
) -> list[dict[str, Any]]:
    """Shortcut for `Stac(stac_url, ...).collections()`."""
    with Stac(stac_url, headers=headers, timeout=timeout) as stac:
        return stac.collections()


def download_asset(
    stac_url: str,
    collection: str,
    item_id: str,
    asset_key: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Path:
    """Shortcut for `Stac(stac_url, ...).download_asset(...)`."""
    with Stac(stac_url, headers=headers, timeout=timeout) as stac:
        return stac.download_asset(collection, item_id, asset_key, dest)
