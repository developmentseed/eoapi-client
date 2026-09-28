"""Tests for the raster (titiler-pgstac) client."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from eoapi_client import EoApiError, Raster

RASTER_URL = "https://example.com/raster"
TILEJSON = {
    "tilejson": "2.2.0",
    "bounds": [-180, -90, 180, 90],
    "minzoom": 0,
    "maxzoom": 22,
    "tiles": [f"{RASTER_URL}/searches/abc123/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}"],
}


@respx.mock
def test_register_search() -> None:
    respx.post(f"{RASTER_URL}/searches/register").mock(return_value=httpx.Response(200, json={"id": "abc123", "links": []}))

    search_id = Raster(RASTER_URL, headers={"Authorization": "Bearer token"}).register_search(
        {"collections": ["my-collection"]}
    )

    assert search_id == "abc123"
    request = respx.calls.last.request
    assert request.headers["Authorization"] == "Bearer token"
    assert json.loads(request.content) == {"collections": ["my-collection"]}


@respx.mock
def test_register_search_error() -> None:
    respx.post(f"{RASTER_URL}/searches/register").mock(return_value=httpx.Response(422, text="bad search"))

    with pytest.raises(EoApiError) as exc_info:
        Raster(RASTER_URL).register_search({"collections": ["my-collection"]})

    assert exc_info.value.status_code == 422


@respx.mock
def test_tilejson() -> None:
    respx.get(f"{RASTER_URL}/searches/abc123/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    data = Raster(RASTER_URL).tilejson("abc123")

    assert data["minzoom"] == 0
    assert data["tiles"] == TILEJSON["tiles"]


@respx.mock
def test_tilejson_passes_params() -> None:
    route = respx.get(f"{RASTER_URL}/searches/abc123/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    Raster(RASTER_URL).tilejson("abc123", assets="data", rescale="0,10000")

    request = route.calls.last.request
    assert request.url.params["assets"] == "data"
    assert request.url.params["rescale"] == "0,10000"


@respx.mock
def test_tile_url_template() -> None:
    respx.get(f"{RASTER_URL}/searches/abc123/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    url = Raster(RASTER_URL).tile_url_template("abc123")

    assert url == TILEJSON["tiles"][0]


@respx.mock
def test_collection_tilejson() -> None:
    respx.get(f"{RASTER_URL}/collections/my-collection/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    data = Raster(RASTER_URL).collection_tilejson("my-collection")

    assert data["tiles"] == TILEJSON["tiles"]


@respx.mock
def test_tilejson_error() -> None:
    respx.get(f"{RASTER_URL}/searches/missing/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with pytest.raises(EoApiError) as exc_info:
        Raster(RASTER_URL).tilejson("missing")

    assert exc_info.value.status_code == 404
