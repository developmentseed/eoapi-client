# eoapi-client

Python client for [eoAPI](https://eoapi.dev).

> [!WARNING]
> This project is in early development. The API is not stable yet.

## Installation

```bash
uv add eoapi-client
```

## Usage

Create and delete STAC items via the [Transactions
extension](https://github.com/stac-api-extensions/transaction):

```python
from eoapi_client import Transactions

tx = Transactions("https://example.com/stac", headers={"Authorization": "Bearer ..."})
created = tx.add_item("my-collection", "./item.geojson")  # local path or URL
tx.delete_item("my-collection", created["id"])
```

Non-2xx responses raise `TransactionError`, which carries the response's
`status_code`.

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
storage, a CDN) that shouldn't receive the STAC API's bearer token. Errors
raise `EoApiError` (or its subclasses `AssetNotFoundError` /
`UnsupportedAssetSchemeError`), which carries the response's `status_code`
when there is one.

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
whole collection's mosaic without registering a search first. Errors raise
`EoApiError`.

## Development

```bash
uv sync
uv run pytest
uv run pre-commit install
```

## License

[MIT](LICENSE)
