"""STAC Transactions through stac-auth-proxy against a live deployment."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from eoapi_client import EoApi, EoApiError, TransactionError, Transactions

from .conftest import SAMPLE_COLLECTION, new_collection_body, unique_id


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


@pytest.fixture
def item_ids(api: EoApi) -> Iterator[list[str]]:
    """Ids for items a test creates in the sample collection; deleted afterwards."""
    ids: list[str] = []
    yield ids
    for item_id in ids:
        try:
            api.transactions.delete_item(SAMPLE_COLLECTION, item_id)
        except EoApiError as exc:
            if exc.status_code != 404:
                raise


def test_item_update_and_patch(api: EoApi, sample_item: dict[str, Any], item_ids: list[str]) -> None:
    item = {**sample_item, "id": unique_id(), "links": []}
    item_ids.append(item["id"])
    api.transactions.add_item(SAMPLE_COLLECTION, item)

    api.transactions.update_item(SAMPLE_COLLECTION, {**item, "properties": {**item["properties"], "title": "updated"}})
    api.transactions.patch_item(SAMPLE_COLLECTION, item["id"], {"properties": {"patched": 1}})

    properties = api.stac.get_item(SAMPLE_COLLECTION, item["id"])["properties"]
    assert properties["title"] == "updated"
    assert properties["patched"] == 1


def test_bulk_add_items(api: EoApi, sample_item: dict[str, Any], item_ids: list[str]) -> None:
    items = [{**sample_item, "id": unique_id(), "links": []} for _ in range(3)]
    item_ids.extend(item["id"] for item in items)

    api.transactions.bulk_add_items(SAMPLE_COLLECTION, items, chunk_size=2)
    api.transactions.bulk_add_items(SAMPLE_COLLECTION, items, method="upsert")

    for item in items:
        assert api.stac.get_item(SAMPLE_COLLECTION, item["id"])["id"] == item["id"]


def test_collection_round_trip(api: EoApi) -> None:
    collection = new_collection_body(unique_id())
    tx = api.transactions
    tx.add_collection(collection)
    try:
        tx.patch_collection(collection["id"], {"description": "patched"})
        assert api.stac.get_collection(collection["id"])["description"] == "patched"

        tx.update_collection({**collection, "title": "updated"})
        assert api.stac.get_collection(collection["id"])["title"] == "updated"
    finally:
        tx.delete_collection(collection["id"])

    with pytest.raises(EoApiError) as exc_info:
        api.stac.get_collection(collection["id"])
    assert exc_info.value.status_code == 404
