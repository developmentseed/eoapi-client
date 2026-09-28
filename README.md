# eoapi-client

Python client for [eoAPI](https://eoapi.dev).

> [!WARNING]
> This project is in early development. The API is not stable yet.

## Installation

```bash
uv add eoapi-client
```

## Usage

`EoApi` bundles all services of one deployment behind one shared HTTP
client (connection reuse, redirects, connection retries):

```python
from pathlib import Path
from eoapi_client import EoApi

with EoApi("https://example.com", headers={"Authorization": "Bearer ..."}) as api:
    api.stac.collections()
    api.stac.get_item("my-collection", "item-1")
    api.stac.download_asset("my-collection", "item-1", "data", Path("./data.tif"))
    api.transactions.add_item("my-collection", "./item.geojson")
    api.raster.tile_url_template(api.raster.register_search({"collections": ["my-collection"]}))
    api.vector().collections()
```

Service URLs default to eoapi-k8s's ingress paths (`/stac`, `/raster`,
`/vector`) under the base URL; override any with `stac_url=`, `raster_url=`
or `vector_url=`. Pass `client=` to use your own `httpx.Client`, and
`timeout=` (default 60s) otherwise.

Each service also works on its own, as shown below. `Stac`, `Transactions`
and `Raster` take `(url, *, headers=None, client=None, timeout=60.0)`.

Create and delete STAC items via the [Transactions
extension](https://github.com/stac-api-extensions/transaction):

```python
from eoapi_client import Transactions

tx = Transactions("https://example.com/stac", headers={"Authorization": "Bearer ..."})
created = tx.add_item("my-collection", "./item.geojson")  # local path or URL
tx.delete_item("my-collection", created["id"])
```

List STAC collections (plain HTTP, so it tolerates collections that fail
`pystac_client`'s stricter validation) and download an item's asset:

```python
from pathlib import Path
from eoapi_client import list_collections, download_asset

collections = list_collections("https://example.com/stac", headers={"Authorization": "Bearer ..."})
download_asset("https://example.com/stac", "my-collection", "item-1", "data", Path("./data.tif"))
```

`download_asset` only forwards the given headers to the asset href when it
shares the STAC API's host — asset hrefs often point elsewhere (object
storage, a CDN) that shouldn't receive the STAC API's bearer token.

Turn a STAC search into map tiles via
[titiler-pgstac](https://stac-utils.github.io/titiler-pgstac/)'s mosaic
endpoints:

```python
from eoapi_client import Raster

raster = Raster("https://example.com/raster", headers={"Authorization": "Bearer ..."})
search_id = raster.register_search({"collections": ["my-collection"]})
tile_url = raster.tile_url_template(search_id, assets="data")
# -> "https://example.com/raster/searches/<id>/tiles/WebMercatorQuad/{z}/{x}/{y}?assets=data"
```

Extra keyword arguments (`assets`, `expression`, `rescale`,
`colormap_name`, ...) are forwarded as query parameters to titiler. Use
`raster.collection_tilejson(collection_id, ...)` instead when you want a
whole collection's mosaic without registering a search first.

Query vector collections (tipg's OGC API - Features) via
[OWSLib](https://owslib.readthedocs.io/en/latest/usage.html#ogc-api-features)
— tipg's `/collections`, `/collections/{id}/items`, and CQL2 filtering are
already well covered there, so this only wires up eoAPI's URL/header
conventions instead of reimplementing a features client. Requires the
`vector` extra: `uv add eoapi-client[vector]`.

```python
from eoapi_client import open_features

features = open_features("https://example.com/vector", headers={"Authorization": "Bearer ..."})
collections = features.collections()
items = features.collection_items("my-collection", **{"filter": "ogc_fid = 3", "filter-lang": "cql2-text"})
```

`open_features()` returns a plain `owslib.ogcapi.features.Features` — see
its docs for the full API (`collection_item()`, `collection_queryables()`,
item writes, ...). OWSLib raises its own errors; see [Errors](#errors).

## Errors

Every failure raised by eoapi-client is an `EoApiError`:

- `EoApiError`: HTTP failure, with `status_code`, `url`, `method` and `body`
  (the response text).
  - `EoApiConnectionError`: no response (DNS, connection refused, timeout).
  - `TransactionError`: a Transactions request failed.
  - `AssetNotFoundError` / `UnsupportedAssetSchemeError`: from `download_asset`.

The exception is `open_features()`: OWSLib raises a plain `RuntimeError` on
non-2xx responses, with no status code attached.

## Development

```bash
uv sync
uv run pytest
uv run pre-commit install
```

Integration tests run against a live
[eoapi-k8s](https://github.com/developmentseed/eoapi-k8s) deployment (with its
mock OIDC server and sample data) and are skipped unless `EOAPI_URL` is set:

```bash
EOAPI_URL=http://localhost uv run pytest tests/integration
```

## License

[MIT](LICENSE)
