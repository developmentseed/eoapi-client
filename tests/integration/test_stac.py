"""STAC reads against a live deployment."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import Any

import httpx
import pytest

from eoapi_client import EoApi

from .conftest import SAMPLE_COLLECTION


def test_collections(api: EoApi) -> None:
    assert SAMPLE_COLLECTION in [c["id"] for c in api.stac.collections()]


def test_get_item(api: EoApi, sample_item: dict[str, Any]) -> None:
    assert api.stac.get_item(SAMPLE_COLLECTION, sample_item["id"])["id"] == sample_item["id"]


def test_download_asset(api: EoApi, sample_item: dict[str, Any], tmp_path: Path) -> None:
    dest = api.stac.download_asset(SAMPLE_COLLECTION, sample_item["id"], "cog", tmp_path / "cog.tif")

    assert dest.read_bytes()[:4] in (b"II*\x00", b"MM\x00*")


@pytest.fixture
def extra_collections(eoapi_url: str, auth: dict[str, str]) -> Iterator[list[str]]:
    """Two temporary collections, so `/collections` has more than one page at `limit=1`."""
    ids = [f"eoapi-client-it-{uuid.uuid4().hex[:8]}" for _ in range(2)]
    extent = {"spatial": {"bbox": [[-180, -90, 180, 90]]}, "temporal": {"interval": [[None, None]]}}
    for collection_id in ids:
        body = {
            "type": "Collection",
            "stac_version": "1.0.0",
            "id": collection_id,
            "description": "eoapi-client test",
            "license": "proprietary",
            "extent": extent,
            "links": [],
        }
        httpx.post(f"{eoapi_url}/stac/collections", json=body, headers=auth).raise_for_status()
    yield ids
    for collection_id in ids:
        httpx.delete(f"{eoapi_url}/stac/collections/{collection_id}", headers=auth)


def test_collections_pagination(api: EoApi, extra_collections: list[str]) -> None:
    ids = [c["id"] for c in api.stac.collections(limit=1)]

    assert {SAMPLE_COLLECTION, *extra_collections} <= set(ids)
    assert len(ids) == len(set(ids))


def test_collections_search(api: EoApi) -> None:
    assert SAMPLE_COLLECTION in [c["id"] for c in api.stac.collections(q="noaa")]


def test_iter_items_pagination(api: EoApi) -> None:
    ids = [item["id"] for item in islice(api.stac.iter_items(SAMPLE_COLLECTION, limit=2), 5)]

    assert len(set(ids)) == 5
