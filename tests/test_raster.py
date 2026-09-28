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

    data = Raster(RASTER_URL).search("abc123").tilejson()

    assert data["minzoom"] == 0
    assert data["tiles"] == TILEJSON["tiles"]


@respx.mock
def test_tilejson_passes_params() -> None:
    route = respx.get(f"{RASTER_URL}/searches/abc123/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    Raster(RASTER_URL).search("abc123").tilejson(assets="data", rescale="0,10000")

    request = route.calls.last.request
    assert request.url.params["assets"] == "data"
    assert request.url.params["rescale"] == "0,10000"


@respx.mock
def test_tile_url_template() -> None:
    respx.get(f"{RASTER_URL}/searches/abc123/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    url = Raster(RASTER_URL).search("abc123").tile_url_template()

    assert url == TILEJSON["tiles"][0]


@respx.mock
def test_collection_tilejson() -> None:
    respx.get(f"{RASTER_URL}/collections/my-collection/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(200, json=TILEJSON)
    )

    data = Raster(RASTER_URL).collection("my-collection").tilejson()

    assert data["tiles"] == TILEJSON["tiles"]


@respx.mock
def test_tilejson_error() -> None:
    respx.get(f"{RASTER_URL}/searches/missing/WebMercatorQuad/tilejson.json").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with pytest.raises(EoApiError) as exc_info:
        Raster(RASTER_URL).search("missing").tilejson()

    assert exc_info.value.status_code == 404


ITEM_PREFIX = f"{RASTER_URL}/collections/c1/items/i1"


@respx.mock
def test_info_per_level() -> None:
    routes = [
        respx.get(f"{ITEM_PREFIX}/info").mock(return_value=httpx.Response(200, json={"level": "item"})),
        respx.get(f"{RASTER_URL}/collections/c1/info").mock(return_value=httpx.Response(200, json={"level": "collection"})),
        respx.get(f"{RASTER_URL}/searches/s1/info").mock(return_value=httpx.Response(200, json={"level": "search"})),
    ]
    raster = Raster(RASTER_URL)

    assert raster.item("c1", "i1").info()["level"] == "item"
    assert raster.collection("c1").info()["level"] == "collection"
    assert raster.search("s1").info()["level"] == "search"
    assert all(route.called for route in routes)


@respx.mock
def test_point() -> None:
    route = respx.get(f"{ITEM_PREFIX}/point/-86.4,36.2").mock(return_value=httpx.Response(200, json={"values": [1]}))

    assert Raster(RASTER_URL).item("c1", "i1").point(-86.4, 36.2, assets="cog")["values"] == [1]
    assert route.calls.last.request.url.params["assets"] == "cog"


@respx.mock
def test_statistics_get_and_post() -> None:
    get = respx.get(f"{ITEM_PREFIX}/statistics").mock(return_value=httpx.Response(200, json={"b1": {}}))
    post = respx.post(f"{RASTER_URL}/collections/c1/statistics").mock(return_value=httpx.Response(200, json={}))
    feature = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {}}
    raster = Raster(RASTER_URL)

    raster.item("c1", "i1").statistics(assets="cog")
    raster.collection("c1").statistics(feature, assets="cog")

    assert get.called
    assert json.loads(post.calls.last.request.content) == feature


@respx.mock
def test_bbox_and_no_data() -> None:
    respx.get(f"{ITEM_PREFIX}/bbox/1,2,3,4/256x256.png").mock(return_value=httpx.Response(200, content=b"png"))
    respx.get(f"{ITEM_PREFIX}/bbox/5,6,7,8.png").mock(return_value=httpx.Response(204))
    item = Raster(RASTER_URL).item("c1", "i1")

    assert item.bbox((1, 2, 3, 4), width=256, height=256) == b"png"
    assert item.bbox((5, 6, 7, 8)) is None


@respx.mock
def test_preview() -> None:
    respx.get(f"{ITEM_PREFIX}/preview.jpeg").mock(return_value=httpx.Response(200, content=b"jpeg"))

    assert Raster(RASTER_URL).item("c1", "i1").preview(format="jpeg") == b"jpeg"


@respx.mock
def test_list_params_repeat() -> None:
    route = respx.get(f"{ITEM_PREFIX}/info").mock(return_value=httpx.Response(200, json={}))

    Raster(RASTER_URL).item("c1", "i1").info(assets=["a", "b"])

    assert route.calls.last.request.url.params.get_list("assets") == ["a", "b"]
