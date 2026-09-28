"""STAC reads against a live deployment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eoapi_client import EoApi

from .conftest import SAMPLE_COLLECTION


def test_collections(api: EoApi) -> None:
    assert SAMPLE_COLLECTION in [c["id"] for c in api.stac.collections()]


def test_get_item(api: EoApi, sample_item: dict[str, Any]) -> None:
    assert api.stac.get_item(SAMPLE_COLLECTION, sample_item["id"])["id"] == sample_item["id"]


def test_download_asset(api: EoApi, sample_item: dict[str, Any], tmp_path: Path) -> None:
    dest = api.stac.download_asset(SAMPLE_COLLECTION, sample_item["id"], "cog", tmp_path / "cog.tif")

    assert dest.read_bytes()[:4] in (b"II*\x00", b"MM\x00*")
