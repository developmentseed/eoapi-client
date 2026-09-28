"""STAC reads against a live deployment."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import Any

import pytest

from eoapi_client import EoApi

from .conftest import SAMPLE_COLLECTION, new_collection_body, unique_id


def test_collections(api: EoApi) -> None:
    assert SAMPLE_COLLECTION in [c["id"] for c in api.stac.collections()]


def test_get_item(api: EoApi, sample_item: dict[str, Any]) -> None:
    assert api.stac.get_item(SAMPLE_COLLECTION, sample_item["id"])["id"] == sample_item["id"]


def test_download_asset(api: EoApi, sample_item: dict[str, Any], tmp_path: Path) -> None:
    dest = api.stac.download_asset(SAMPLE_COLLECTION, sample_item["id"], "cog", tmp_path / "cog.tif")

    assert dest.read_bytes()[:4] in (b"II*\x00", b"MM\x00*")


@pytest.fixture
def extra_collections(api: EoApi) -> Iterator[list[str]]:
    """Two temporary collections, so `/collections` has more than one page at `limit=1`."""
    ids = [unique_id() for _ in range(2)]
    for collection_id in ids:
        api.transactions.add_collection(new_collection_body(collection_id))
    yield ids
    for collection_id in ids:
        api.transactions.delete_collection(collection_id)


def test_collections_pagination(api: EoApi, extra_collections: list[str]) -> None:
    ids = [c["id"] for c in api.stac.collections(limit=1)]

    assert {SAMPLE_COLLECTION, *extra_collections} <= set(ids)
    assert len(ids) == len(set(ids))


def test_collections_search(api: EoApi) -> None:
    assert SAMPLE_COLLECTION in [c["id"] for c in api.stac.collections(q="noaa")]


def test_iter_items_pagination(api: EoApi) -> None:
    ids = [item["id"] for item in islice(api.stac.iter_items(SAMPLE_COLLECTION, limit=2), 5)]

    assert len(set(ids)) == 5
