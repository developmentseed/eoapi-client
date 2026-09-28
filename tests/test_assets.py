"""Tests for STAC asset downloads."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from eoapi_client import AssetNotFoundError, EoApiConnectionError, EoApiError, UnsupportedAssetSchemeError, download_asset

STAC_URL = "https://example.com/stac"
ITEM_WITH_ASSET = {
    "id": "item-1",
    "collection": "coll-1",
    "assets": {"data": {"href": f"{STAC_URL}/collections/coll-1/items/item-1/data"}},
}


@respx.mock
def test_download_asset(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(
        return_value=httpx.Response(200, content=b"asset-bytes")
    )

    dest = tmp_path / "out" / "asset.bin"
    path = download_asset(STAC_URL, "coll-1", "item-1", "data", dest, headers={"Authorization": "Bearer token"})

    assert path == dest
    assert dest.read_bytes() == b"asset-bytes"


@respx.mock
def test_download_asset_unknown_key() -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))

    with pytest.raises(AssetNotFoundError, match="missing"):
        download_asset(STAC_URL, "coll-1", "item-1", "missing", Path("out.bin"))


@respx.mock
def test_download_asset_item_not_found() -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(404, text="not found"))

    with pytest.raises(EoApiError) as exc_info:
        download_asset(STAC_URL, "coll-1", "item-1", "data", Path("out.bin"))

    assert exc_info.value.status_code == 404


@respx.mock
def test_download_asset_strips_bearer_cross_host(tmp_path: Path) -> None:
    item = {
        "id": "item-1",
        "collection": "coll-1",
        "assets": {"data": {"href": "https://other-host.example.com/data.bin"}},
    }
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=item))
    asset_route = respx.get("https://other-host.example.com/data.bin").mock(
        return_value=httpx.Response(200, content=b"asset-bytes")
    )

    download_asset(STAC_URL, "coll-1", "item-1", "data", tmp_path / "out.bin", headers={"Authorization": "Bearer token"})

    assert "Authorization" not in asset_route.calls.last.request.headers


@respx.mock
def test_download_asset_forwards_bearer_same_host(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    asset_route = respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(
        return_value=httpx.Response(200, content=b"asset-bytes")
    )

    download_asset(STAC_URL, "coll-1", "item-1", "data", tmp_path / "out.bin", headers={"Authorization": "Bearer token"})

    assert asset_route.calls.last.request.headers["Authorization"] == "Bearer token"


@respx.mock
def test_download_asset_unsupported_scheme() -> None:
    item = {
        "id": "item-1",
        "collection": "coll-1",
        "assets": {"data": {"href": "file:///eodata/sentinel/example.jp2"}},
    }
    route = respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=item))

    with pytest.raises(UnsupportedAssetSchemeError, match="unsupported scheme"):
        download_asset(STAC_URL, "coll-1", "item-1", "data", Path("out.bin"))

    assert route.call_count == 1


@respx.mock
def test_download_asset_href_error(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(EoApiError) as exc_info:
        download_asset(STAC_URL, "coll-1", "item-1", "data", tmp_path / "out.bin")

    assert exc_info.value.status_code == 500
    assert exc_info.value.body == "boom"


@respx.mock
def test_download_asset_connection_error(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(EoApiConnectionError):
        download_asset(STAC_URL, "coll-1", "item-1", "data", tmp_path / "out.bin")
