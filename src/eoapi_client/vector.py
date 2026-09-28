"""Vector (OGC API - Features) access via tipg.

tipg implements OGC API - Features, including Part 3 (Filtering / CQL2),
which `owslib.ogcapi.features.Features` already covers well: header
passthrough (for auth) and `filter`/`filter-lang` are both plain
pass-through query parameters, so there is nothing tipg-specific left to
reimplement. This module only wires eoAPI's URL/header conventions into
OWSLib.

Requires the optional `owslib` dependency: `pip install eoapi-client[vector]`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
