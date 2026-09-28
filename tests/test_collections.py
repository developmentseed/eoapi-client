"""Tests for STAC collection listing."""

from __future__ import annotations

from itertools import islice

import httpx
import pytest
import respx

from eoapi_client import EoApiConnectionError, EoApiError, Stac

STAC_URL = "https://example.com/stac"


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
