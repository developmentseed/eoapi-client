"""Tests for STAC reads: collections, items and asset downloads."""

from __future__ import annotations

from itertools import islice
from pathlib import Path

import httpx
import pytest
import respx

from eoapi_client import AssetNotFoundError, EoApiConnectionError, EoApiError, Stac, UnsupportedAssetSchemeError

STAC_URL = "https://example.com/stac"
ITEM_WITH_ASSET = {
    "id": "item-1",
    "collection": "coll-1",
    "assets": {"data": {"href": f"{STAC_URL}/collections/coll-1/items/item-1/data"}},
}


@respx.mock
def test_list_collections() -> None:
    respx.get(f"{STAC_URL}/collections").mock(
        return_value=httpx.Response(200, json={"collections": [{"id": "coll-1"}, {"id": "coll-2"}]})
    )

    collections = Stac(STAC_URL, headers={"Authorization": "Bearer token"}).collections()

    assert [c["id"] for c in collections] == ["coll-1", "coll-2"]
    assert respx.calls.last.request.headers["Authorization"] == "Bearer token"


@respx.mock
def test_list_collections_empty() -> None:
    respx.get(f"{STAC_URL}/collections").mock(return_value=httpx.Response(200, json={}))

    assert Stac(STAC_URL).collections() == []


@respx.mock
def test_list_collections_error() -> None:
    respx.get(f"{STAC_URL}/collections").mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(EoApiError) as exc_info:
        Stac(STAC_URL).collections()

    assert exc_info.value.status_code == 500


@respx.mock
def test_list_collections_connection_error() -> None:
    respx.get(f"{STAC_URL}/collections").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(EoApiConnectionError):
        Stac(STAC_URL).collections()


def _page(key: str, ids: list[str], next_href: str | None = None) -> httpx.Response:
    links = [{"rel": "next", "href": next_href}] if next_href else []
    return httpx.Response(200, json={key: [{"id": i} for i in ids], "links": links})


@respx.mock
def test_collections_follows_next() -> None:
    page_2 = f"{STAC_URL}/collections?q=x&limit=1&offset=1"
    second = respx.get(page_2).mock(return_value=_page("collections", ["b"]))
    first = respx.get(f"{STAC_URL}/collections").mock(return_value=_page("collections", ["a"], page_2))

    collections = Stac(STAC_URL).collections(q="x", limit=1)

    assert [c["id"] for c in collections] == ["a", "b"]
    assert dict(first.calls.last.request.url.params) == {"q": "x", "limit": "1"}
    assert dict(second.calls.last.request.url.params) == {"q": "x", "limit": "1", "offset": "1"}


@respx.mock
def test_collections_stops_on_repeated_next() -> None:
    route = respx.get(f"{STAC_URL}/collections").mock(return_value=_page("collections", ["a"], f"{STAC_URL}/collections"))

    assert [c["id"] for c in Stac(STAC_URL).collections()] == ["a"]
    assert route.call_count == 1


@respx.mock
def test_iter_collections_is_lazy() -> None:
    page_2 = respx.get(f"{STAC_URL}/collections?offset=1").mock(return_value=_page("collections", ["b"]))
    respx.get(f"{STAC_URL}/collections").mock(return_value=_page("collections", ["a"], f"{STAC_URL}/collections?offset=1"))

    assert [c["id"] for c in islice(Stac(STAC_URL).iter_collections(), 1)] == ["a"]
    assert not page_2.called


@respx.mock
def test_iter_items_follows_next() -> None:
    items_url = f"{STAC_URL}/collections/coll-1/items"
    respx.get(f"{items_url}?token=t").mock(return_value=_page("features", ["i3"]))
    respx.get(items_url).mock(return_value=_page("features", ["i1", "i2"], f"{items_url}?token=t"))

    assert [i["id"] for i in Stac(STAC_URL).iter_items("coll-1")] == ["i1", "i2", "i3"]


@respx.mock
def test_get_collection() -> None:
    respx.get(f"{STAC_URL}/collections/coll-1").mock(return_value=httpx.Response(200, json={"id": "coll-1"}))

    assert Stac(STAC_URL).get_collection("coll-1") == {"id": "coll-1"}


@respx.mock
def test_download_asset(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(
        return_value=httpx.Response(200, content=b"asset-bytes")
    )

    dest = tmp_path / "out" / "asset.bin"
    path = Stac(STAC_URL, headers={"Authorization": "Bearer token"}).download_asset("coll-1", "item-1", "data", dest)

    assert path == dest
    assert dest.read_bytes() == b"asset-bytes"


@respx.mock
def test_download_asset_unknown_key() -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))

    with pytest.raises(AssetNotFoundError, match="missing"):
        Stac(STAC_URL).download_asset("coll-1", "item-1", "missing", Path("out.bin"))


@respx.mock
def test_download_asset_item_not_found() -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(404, text="not found"))

    with pytest.raises(EoApiError) as exc_info:
        Stac(STAC_URL).download_asset("coll-1", "item-1", "data", Path("out.bin"))

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

    Stac(STAC_URL, headers={"Authorization": "Bearer token"}).download_asset(
        "coll-1", "item-1", "data", tmp_path / "out.bin"
    )

    assert "Authorization" not in asset_route.calls.last.request.headers


@respx.mock
def test_download_asset_forwards_bearer_same_host(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    asset_route = respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(
        return_value=httpx.Response(200, content=b"asset-bytes")
    )

    Stac(STAC_URL, headers={"Authorization": "Bearer token"}).download_asset(
        "coll-1", "item-1", "data", tmp_path / "out.bin"
    )

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
        Stac(STAC_URL).download_asset("coll-1", "item-1", "data", Path("out.bin"))

    assert route.call_count == 1


@respx.mock
def test_download_asset_href_error(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(EoApiError) as exc_info:
        Stac(STAC_URL).download_asset("coll-1", "item-1", "data", tmp_path / "out.bin")

    assert exc_info.value.status_code == 500
    assert exc_info.value.body == "boom"


@respx.mock
def test_download_asset_connection_error(tmp_path: Path) -> None:
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1").mock(return_value=httpx.Response(200, json=ITEM_WITH_ASSET))
    respx.get(f"{STAC_URL}/collections/coll-1/items/item-1/data").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(EoApiConnectionError):
        Stac(STAC_URL).download_asset("coll-1", "item-1", "data", tmp_path / "out.bin")
