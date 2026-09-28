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
    template = api.raster.tile_url_template(search_id, assets="cog")
    minx, miny, maxx, maxy = sample_item["bbox"]
    x, y = _tile((minx + maxx) / 2, (miny + maxy) / 2, 14)

    response = httpx.get(template.format(z=14, x=x, y=y))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_collection_tilejson(api: EoApi) -> None:
    assert api.raster.collection_tilejson(SAMPLE_COLLECTION, assets="cog")["tiles"]
