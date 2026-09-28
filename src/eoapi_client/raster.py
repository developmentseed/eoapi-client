"""Raster tile access via titiler-pgstac's STAC-search mosaics.

https://stac-utils.github.io/titiler-pgstac/
"""

from __future__ import annotations

from typing import Any

from eoapi_client._http import get_json, post_json

DEFAULT_TILE_MATRIX_SET = "WebMercatorQuad"


class Raster:
    """Register STAC searches as tile mosaics and fetch their TileJSON/tile URLs."""

    def __init__(self, raster_url: str, *, headers: dict[str, str] | None = None) -> None:
        self._raster_url = raster_url.rstrip("/")
        self._headers = headers or {}

    def register_search(self, search_body: dict[str, Any]) -> str:
        """Register a STAC search as a mosaic via `POST /searches/register`.

        `search_body` is a STAC search filter (`collections`, `bbox`,
        `datetime`, `query`/`filter`, ...), optionally with a nested
        `metadata` key (`assets`, `minzoom`, `maxzoom`, `defaults`, ...).
        Returns the mosaic's `search_id`, to pass to `tilejson()` /
        `tile_url_template()`.
        """
        url = f"{self._raster_url}/searches/register"
        data = post_json(url, json=search_body, headers=self._headers, timeout=30.0)
        return str(data["id"])

    def tilejson(
        self,
        search_id: str,
        *,
        tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET,
        **params: Any,
    ) -> dict[str, Any]:
        """Fetch a registered search's TileJSON.

        `GET /searches/{search_id}/{tile_matrix_set}/tilejson.json`. Extra
        keyword arguments (`assets`, `expression`, `rescale`,
        `colormap_name`, ...) are passed through as query parameters.
        """
        url = f"{self._raster_url}/searches/{search_id}/{tile_matrix_set}/tilejson.json"
        return dict(get_json(url, headers=self._headers, params=params, timeout=30.0))

    def tile_url_template(
        self,
        search_id: str,
        *,
        tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET,
        **params: Any,
    ) -> str:
        """Return the registered search's `{z}/{x}/{y}` tile URL template.

        Ready to hand to a map viewer (Leaflet, MapLibre, ...) without
        hand-building titiler query strings.
        """
        data = self.tilejson(search_id, tile_matrix_set=tile_matrix_set, **params)
        return str(data["tiles"][0])

    def collection_tilejson(
        self,
        collection_id: str,
        *,
        tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET,
        **params: Any,
    ) -> dict[str, Any]:
        """Fetch a whole collection's TileJSON, without registering a search first.

        `GET /collections/{collection_id}/{tile_matrix_set}/tilejson.json`.
        """
        url = f"{self._raster_url}/collections/{collection_id}/{tile_matrix_set}/tilejson.json"
        return dict(get_json(url, headers=self._headers, params=params, timeout=30.0))
