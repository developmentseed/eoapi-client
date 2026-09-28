"""tipg via OWSLib against a live deployment."""

from __future__ import annotations

import httpx

from eoapi_client import EoApi

SAMPLE_TABLE = "public.my_data"


def test_collections(api: EoApi) -> None:
    assert SAMPLE_TABLE in [c["id"] for c in api.vector().collections()["collections"]]


def test_collection_items(api: EoApi) -> None:
    assert len(api.vector().collection_items(SAMPLE_TABLE, limit=2)["features"]) == 2


def test_cql2_filter(api: EoApi) -> None:
    items = api.vector().collection_items(SAMPLE_TABLE, **{"filter": "ogc_fid = 3", "filter-lang": "cql2-text"})

    assert [f["properties"]["ogc_fid"] for f in items["features"]] == [3]


def test_vector_tiles(api: EoApi) -> None:
    vt = api.vector_tiles

    assert vt.tilejson(SAMPLE_TABLE)["vector_layers"]
    assert vt.style_json(SAMPLE_TABLE)["version"] == 8
    assert vt.tile(SAMPLE_TABLE, 0, 0, 0)

    response = httpx.get(vt.tile_url_template(SAMPLE_TABLE).format(z=0, x=0, y=0))
    assert response.headers["content-type"] == "application/vnd.mapbox-vector-tile"
