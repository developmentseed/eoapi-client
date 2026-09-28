"""Raster access via titiler-pgstac: search mosaics, collections and single items.

https://stac-utils.github.io/titiler-pgstac/
"""

from __future__ import annotations

from typing import Any

import httpx

from eoapi_client._http import Service

DEFAULT_TILE_MATRIX_SET = "WebMercatorQuad"


def _image(response: httpx.Response) -> bytes | None:
    """The image bytes, or `None` when titiler has no data there (204)."""
    return None if response.status_code == 204 else response.content


def _size(width: int | None, height: int | None) -> str:
    return f"/{width}x{height}" if width and height else ""


class _Target:
    """titiler-pgstac endpoints shared by a registered search, a collection and an item.

    Extra keyword arguments (`assets`, `expression`, `rescale`,
    `colormap_name`, ...) are passed through as query parameters; lists
    become repeated keys (`assets=["a", "b"]` → `assets=a&assets=b`).
    """

    def __init__(self, raster: Raster, prefix: str) -> None:
        self._raster = raster
        self._prefix = prefix

    def _get(self, path: str, **params: Any) -> httpx.Response:
        return self._raster._request("GET", f"{self._prefix}{path}", params=params)

    def info(self, **params: Any) -> dict[str, Any]:
        return dict(self._get("/info", **params).json())

    def tilejson(self, *, tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET, **params: Any) -> dict[str, Any]:
        return dict(self._get(f"/{tile_matrix_set}/tilejson.json", **params).json())

    def tile_url_template(self, *, tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET, **params: Any) -> str:
        """The `{z}/{x}/{y}` tile URL template, ready for a map viewer (Leaflet, MapLibre, ...)."""
        return str(self.tilejson(tile_matrix_set=tile_matrix_set, **params)["tiles"][0])

    def point(self, lon: float, lat: float, **params: Any) -> dict[str, Any]:
        return dict(self._get(f"/point/{lon},{lat}", **params).json())

    def statistics(self, feature: dict[str, Any] | None = None, **params: Any) -> dict[str, Any]:
        """Statistics within a GeoJSON `feature` (POST), or of a whole item (GET, items only)."""
        method = "GET" if feature is None else "POST"
        return dict(self._raster._request(method, f"{self._prefix}/statistics", json=feature, params=params).json())

    def bbox(
        self,
        bbox: tuple[float, float, float, float],
        *,
        format: str = "png",
        width: int | None = None,
        height: int | None = None,
        **params: Any,
    ) -> bytes | None:
        """An image of `bbox` (minx, miny, maxx, maxy), or `None` if titiler returns no data (204)."""
        minx, miny, maxx, maxy = bbox
        return _image(self._get(f"/bbox/{minx},{miny},{maxx},{maxy}{_size(width, height)}.{format}", **params))


class _ItemTarget(_Target):
    def preview(
        self, *, format: str = "png", width: int | None = None, height: int | None = None, **params: Any
    ) -> bytes | None:
        """A preview image of the whole item (`max_size=` limits its size)."""
        return _image(self._get(f"/preview{_size(width, height)}.{format}", **params))


class Raster(Service):
    """titiler-pgstac: register searches as mosaics and query searches, collections or items."""

    def search(self, search_id: str) -> _Target:
        return _Target(self, f"/searches/{search_id}")

    def collection(self, collection_id: str) -> _Target:
        return _Target(self, f"/collections/{collection_id}")

    def item(self, collection_id: str, item_id: str) -> _ItemTarget:
        return _ItemTarget(self, f"/collections/{collection_id}/items/{item_id}")

    def register_search(self, search_body: dict[str, Any]) -> str:
        """Register a STAC search as a mosaic via `POST /searches/register`.

        `search_body` is a STAC search filter (`collections`, `bbox`,
        `datetime`, `query`/`filter`, ...), optionally with a nested
        `metadata` key (`assets`, `minzoom`, `maxzoom`, `defaults`, ...).
        Returns the mosaic's `search_id`, for `search(search_id)`.
        """
        return str(self._request("POST", "/searches/register", json=search_body).json()["id"])
