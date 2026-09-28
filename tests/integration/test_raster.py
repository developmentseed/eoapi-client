"""titiler-pgstac against a live deployment."""

from __future__ import annotations

import math
from typing import Any

import httpx

from eoapi_client import EoApi

from .conftest import SAMPLE_COLLECTION


def _tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2**z
    lat_rad = math.radians(lat)
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n)


def test_search_tile(api: EoApi, sample_item: dict[str, Any]) -> None:
    search_id = api.raster.register_search({"collections": [SAMPLE_COLLECTION]})
    template = api.raster.search(search_id).tile_url_template(assets="cog")
    minx, miny, maxx, maxy = sample_item["bbox"]
    x, y = _tile((minx + maxx) / 2, (miny + maxy) / 2, 14)

    response = httpx.get(template.format(z=14, x=x, y=y))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_collection_tilejson(api: EoApi) -> None:
    assert api.raster.collection(SAMPLE_COLLECTION).tilejson(assets="cog")["tiles"]


def _centre(item: dict[str, Any]) -> tuple[float, float]:
    minx, miny, maxx, maxy = item["bbox"]
    return (minx + maxx) / 2, (miny + maxy) / 2


def test_item_endpoints(api: EoApi, sample_item: dict[str, Any]) -> None:
    item = api.raster.item(SAMPLE_COLLECTION, sample_item["id"])

    assert "bounds" in item.info(assets="cog")["cog"]
    assert (item.preview(assets="cog", max_size=128) or b"").startswith(b"\x89PNG")
    assert len(item.point(*_centre(sample_item), assets="cog")["values"]) == 3
    assert {"min", "max", "mean"} <= set(item.statistics(assets="cog")["b1"])


def test_collection_endpoints(api: EoApi, sample_item: dict[str, Any]) -> None:
    collection = api.raster.collection(SAMPLE_COLLECTION)
    # A small area and max_size: full-resolution statistics over the whole
    # item OOM-kill the raster pod on a local cluster.
    x, y, d = *_centre(sample_item), 0.001
    ring = [[x - d, y - d], [x + d, y - d], [x + d, y + d], [x - d, y + d], [x - d, y - d]]
    feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}

    assert "search" in collection.info()
    assert "statistics" in collection.statistics(feature, assets="cog", max_size=256)["properties"]
    assert (collection.bbox((x - d, y - d, x + d, y + d), assets="cog") or b"").startswith(b"\x89PNG")
