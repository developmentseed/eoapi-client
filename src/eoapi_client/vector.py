"""Vector access via tipg: features through OWSLib, vector tiles through `VectorTiles`.

tipg implements OGC API - Features, including Part 3 (Filtering / CQL2),
which `owslib.ogcapi.features.Features` already covers well: header
passthrough (for auth) and `filter`/`filter-lang` are both plain
pass-through query parameters, so there is nothing tipg-specific left to
reimplement. `open_features` only wires eoAPI's URL/header conventions into
OWSLib, and requires the optional `owslib` dependency:
`pip install eoapi-client[vector]`. OWSLib doesn't cover tipg's vector
tiles (MVT), which `VectorTiles` does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from eoapi_client._http import Service
from eoapi_client.raster import DEFAULT_TILE_MATRIX_SET

if TYPE_CHECKING:
    from owslib.ogcapi.features import Features


def open_features(vector_url: str, *, headers: dict[str, str] | None = None) -> Features:
    """Open an OWSLib `Features` client against a tipg deployment.

    `Features` fetches the landing page immediately on construction, so
    `vector_url` must be reachable when this is called. See
    https://owslib.readthedocs.io/en/latest/usage.html#ogc-api-features for
    the full client API (`collections()`, `collection_items()`,
    `collection_item()`, CQL2 filtering via `filter`/`filter-lang`, ...).

    Non-2xx responses raise a plain `RuntimeError` — OWSLib doesn't expose
    the response's status code.
    """
    try:
        from owslib.ogcapi.features import Features
    except ImportError as exc:  # pragma: no cover
        raise ImportError("owslib is required for vector access — install eoapi-client[vector]") from exc
    return Features(vector_url, headers=headers)


class VectorTiles(Service):
    """tipg vector tiles (MVT) for a collection: a PostGIS table or function, e.g. `public.my_data`.

    Extra keyword arguments (`limit`, `columns`, `filter`, `geom-column`, ...)
    are passed through as query parameters.
    """

    def _get(self, collection_id: str, tile_matrix_set: str, path: str, params: dict[str, Any]) -> httpx.Response:
        return self._request("GET", f"/collections/{collection_id}/tiles/{tile_matrix_set}/{path}", params=params)

    def tilejson(
        self, collection_id: str, *, tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET, **params: Any
    ) -> dict[str, Any]:
        return dict(self._get(collection_id, tile_matrix_set, "tilejson.json", params).json())

    def tile_url_template(self, collection_id: str, *, tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET, **params: Any) -> str:
        """The `{z}/{x}/{y}` tile URL template, ready for a map viewer (MapLibre, ...)."""
        return str(self.tilejson(collection_id, tile_matrix_set=tile_matrix_set, **params)["tiles"][0])

    def style_json(
        self, collection_id: str, *, tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET, **params: Any
    ) -> dict[str, Any]:
        """A MapLibre style for the collection's tiles."""
        return dict(self._get(collection_id, tile_matrix_set, "style.json", params).json())

    def tile(
        self, collection_id: str, z: int, x: int, y: int, *, tile_matrix_set: str = DEFAULT_TILE_MATRIX_SET, **params: Any
    ) -> bytes:
        """One MVT tile; tipg returns empty bytes where there are no features."""
        return bytes(self._get(collection_id, tile_matrix_set, f"{z}/{x}/{y}", params).content)
