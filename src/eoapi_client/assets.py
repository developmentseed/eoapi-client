"""STAC item asset downloads."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from eoapi_client._http import EoApiConnectionError, EoApiError, get_json, raise_for_response


class AssetNotFoundError(EoApiError):
    """The requested asset key doesn't exist on the item."""


class UnsupportedAssetSchemeError(EoApiError):
    """The asset href uses a scheme that can't be fetched over HTTP."""


def download_asset(
    stac_url: str,
    collection: str,
    item_id: str,
    asset_key: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> Path:
    """Resolve an item's asset href and stream it to `dest`.

    Auth headers are only forwarded to the asset href when it shares the
    STAC API's host — asset hrefs commonly point at a different host (object
    storage, a CDN) that shouldn't receive the STAC API's bearer token.
    """
    item_url = f"{stac_url.rstrip('/')}/collections/{collection}/items/{item_id}"
    item = get_json(item_url, headers=headers, timeout=timeout)
    asset = (item.get("assets") or {}).get(asset_key)
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
    asset_headers = headers if headers and parsed_href.netloc == urlparse(item_url).netloc else {}
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            httpx.Client(timeout=timeout, follow_redirects=True) as client,
            client.stream("GET", href, headers=asset_headers) as response,
        ):
            raise_for_response(response)
            with dest.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    except httpx.TransportError as exc:
        raise EoApiConnectionError(f"GET {href} failed: {exc}", url=href, method="GET") from exc
    return dest
