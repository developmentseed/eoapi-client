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
    api.stac.collections(q="sentinel")  # all pages; search params pass through
    for item in api.stac.iter_items("my-collection", datetime="2024-01-01T00:00:00Z/.."):
        ...
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

Write STAC items and collections via the [Transactions
extension](https://github.com/stac-api-extensions/transaction). Items and
collections can be a dict, a pystac object, a local path or a URL:

```python
from eoapi_client import Transactions

tx = Transactions("https://example.com/stac", headers={"Authorization": "Bearer ..."})
created = tx.add_item("my-collection", "./item.geojson")
tx.patch_item("my-collection", created["id"], {"properties": {"title": "New"}})  # JSON merge patch
tx.bulk_add_items("my-collection", items, method="upsert")  # chunked, 500 per request
tx.delete_item("my-collection", created["id"])
```

Items: `add_item`, `update_item` (PUT), `patch_item`, `delete_item`,
`bulk_add_items`. Collections: `add_collection`, `update_collection`,
`patch_collection`, `delete_collection` (pgstac also deletes the
collection's items).

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
`colormap_name`, ...) are forwarded as query parameters to titiler, and lists
become repeated keys. Use `raster.collection_tilejson(collection_id, ...)`
instead when you want a whole collection's mosaic without registering a
search first.

For analysis, `raster.item(collection_id, item_id)`,
`raster.collection(collection_id)` and `raster.search(search_id)` share
`info`, `tilejson`, `tile_url_template`, `point`, `statistics` and `bbox`.
Items also have `preview`:

```python
item = raster.item("my-collection", "item-1")
item.info(assets="data")
png = item.preview(assets="data", max_size=512)  # bytes
item.point(-86.39, 36.21, assets="data")["values"]
item.statistics(assets="data")  # whole item
raster.collection("my-collection").statistics(feature, assets="data", max_size=512)  # within a GeoJSON feature
```

Image methods return `None` when titiler has no data there (HTTP 204).

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

## Auth

Pass `auth=` to `EoApi` (or any service) to have tokens fetched, cached
until shortly before they expire, and refetched once on a 401:

```python
from eoapi_client import EoApi, client_credentials_auth, mock_oidc_auth

# Keycloak (or any OAuth2 client-credentials token endpoint)
auth = client_credentials_auth(
    "https://keycloak.example.com/realms/eoapi/protocol/openid-connect/token",
    client_id="ingest",
    client_secret="...",
)
# eoapi-k8s's mock OIDC server, for testing
auth = mock_oidc_auth("http://localhost/mock-oidc")

api = EoApi("https://example.com", auth=auth)
```

`TokenAuth(fetch)` wraps any other token source: `fetch()` returns a token
string, and its expiry is read from the JWT's `exp` claim. For a static token,
keep using `headers={"Authorization": "Bearer ..."}`. Tokens are only sent to
the configured service URLs, never to asset hosts elsewhere. `api.vector()`
gets the token current at call time, because OWSLib only takes static headers.

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
