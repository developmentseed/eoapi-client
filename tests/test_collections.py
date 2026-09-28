"""Tests for STAC collection listing."""

from __future__ import annotations

import httpx
import pytest
import respx

from eoapi_client import EoApiError, list_collections

STAC_URL = "https://example.com/stac"


@respx.mock
def test_list_collections() -> None:
    respx.get(f"{STAC_URL}/collections").mock(
        return_value=httpx.Response(200, json={"collections": [{"id": "coll-1"}, {"id": "coll-2"}]})
    )

    collections = list_collections(STAC_URL, headers={"Authorization": "Bearer token"})

    assert [c["id"] for c in collections] == ["coll-1", "coll-2"]
    assert respx.calls.last.request.headers["Authorization"] == "Bearer token"


@respx.mock
def test_list_collections_empty() -> None:
    respx.get(f"{STAC_URL}/collections").mock(return_value=httpx.Response(200, json={}))

    assert list_collections(STAC_URL) == []


@respx.mock
def test_list_collections_error() -> None:
    respx.get(f"{STAC_URL}/collections").mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(EoApiError) as exc_info:
        list_collections(STAC_URL)

    assert exc_info.value.status_code == 500
