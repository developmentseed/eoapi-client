"""STAC Transactions through stac-auth-proxy against a live deployment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eoapi_client import EoApi, EoApiError, TransactionError, Transactions

from .conftest import SAMPLE_COLLECTION


def test_add_item_without_token(eoapi_url: str, new_item: Path) -> None:
    with pytest.raises(TransactionError) as exc_info:
        Transactions(f"{eoapi_url}/stac").add_item(SAMPLE_COLLECTION, str(new_item))

    assert exc_info.value.status_code == 401


def test_add_and_delete_item(api: EoApi, new_item: Path) -> None:
    item_id = json.loads(new_item.read_text())["id"]

    assert api.transactions.add_item(SAMPLE_COLLECTION, str(new_item))["id"] == item_id
    assert api.stac.get_item(SAMPLE_COLLECTION, item_id)["id"] == item_id

    api.transactions.delete_item(SAMPLE_COLLECTION, item_id)

    with pytest.raises(EoApiError) as exc_info:
        api.stac.get_item(SAMPLE_COLLECTION, item_id)
    assert exc_info.value.status_code == 404
