"""tipg via OWSLib against a live deployment."""

from __future__ import annotations

from eoapi_client import EoApi

SAMPLE_TABLE = "public.my_data"


def test_collections(api: EoApi) -> None:
    assert SAMPLE_TABLE in [c["id"] for c in api.vector().collections()["collections"]]


def test_collection_items(api: EoApi) -> None:
    assert len(api.vector().collection_items(SAMPLE_TABLE, limit=2)["features"]) == 2


def test_cql2_filter(api: EoApi) -> None:
    items = api.vector().collection_items(SAMPLE_TABLE, **{"filter": "ogc_fid = 3", "filter-lang": "cql2-text"})

    assert [f["properties"]["ogc_fid"] for f in items["features"]] == [3]
