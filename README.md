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

## Development

```bash
uv sync
uv run pytest
uv run pre-commit install
```

## License

[MIT](LICENSE)
