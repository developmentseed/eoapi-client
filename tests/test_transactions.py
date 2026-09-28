"""Tests for the STAC Transactions client."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from eoapi_client import TransactionError, Transactions

STAC_URL = "https://example.com/stac"
ITEM_BODY = (
    b'{"type":"Feature","stac_version":"1.0.0","id":"new-item",'
    b'"collection":"ws-test","geometry":null,"properties":{},'
    b'"links":[],"assets":{}}'
)
ITEM_JSON = {
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "new-item",
    "collection": "ws-test",
    "geometry": None,
    "properties": {},
    "links": [],
    "assets": {},
}


@respx.mock
def test_add_item(tmp_path: Path) -> None:
    item_file = tmp_path / "item.geojson"
    item_file.write_bytes(ITEM_BODY)
    url = f"{STAC_URL}/collections/ws-test/items"
    respx.post(url).mock(return_value=httpx.Response(201, json=ITEM_JSON))

    created = Transactions(STAC_URL, headers={"Authorization": "Bearer token"}).add_item("ws-test", str(item_file))

    assert created["id"] == "new-item"
    request = respx.calls.last.request
    assert request.headers["Authorization"] == "Bearer token"
    assert request.headers["Content-Type"] == "application/geo+json"


@respx.mock
def test_add_item_from_url() -> None:
    body_url = "https://example.com/item.geojson"
    respx.get(body_url).mock(return_value=httpx.Response(200, content=ITEM_BODY))
    respx.post(f"{STAC_URL}/collections/ws-test/items").mock(return_value=httpx.Response(201, json=ITEM_JSON))

    created = Transactions(STAC_URL).add_item("ws-test", body_url)

    assert created["id"] == "new-item"


@respx.mock
def test_delete_item() -> None:
    url = f"{STAC_URL}/collections/ws-test/items/new-item"
    respx.delete(url).mock(return_value=httpx.Response(204))

    Transactions(STAC_URL).delete_item("ws-test", "new-item")


@pytest.mark.parametrize("status", [401, 403, 404, 409, 500])
@respx.mock
def test_add_item_errors(tmp_path: Path, status: int) -> None:
    item_file = tmp_path / "item.geojson"
    item_file.write_bytes(ITEM_BODY)
    url = f"{STAC_URL}/collections/ws-test/items"
    respx.post(url).mock(return_value=httpx.Response(status, text="fail"))

    with pytest.raises(TransactionError) as exc_info:
        Transactions(STAC_URL).add_item("ws-test", str(item_file))

    assert exc_info.value.status_code == status


@respx.mock
def test_delete_item_error() -> None:
    url = f"{STAC_URL}/collections/ws-test/items/missing"
    respx.delete(url).mock(return_value=httpx.Response(404, text="not found"))

    with pytest.raises(TransactionError) as exc_info:
        Transactions(STAC_URL).delete_item("ws-test", "missing")

    assert exc_info.value.status_code == 404
