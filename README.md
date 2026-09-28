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

## Development

```bash
uv sync
uv run pytest
uv run pre-commit install
```

## License

[MIT](LICENSE)
