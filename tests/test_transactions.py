"""Tests for the STAC Transactions client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from eoapi_client import EoApiConnectionError, EoApiError, TransactionError, Transactions

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
    assert request.headers["Content-Type"] == "application/json"


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

    assert isinstance(exc_info.value, EoApiError)
    assert exc_info.value.status_code == status
    assert exc_info.value.method == "POST"
    assert exc_info.value.url == url
    assert exc_info.value.body == "fail"


@respx.mock
def test_delete_item_error() -> None:
    url = f"{STAC_URL}/collections/ws-test/items/missing"
    respx.delete(url).mock(return_value=httpx.Response(404, text="not found"))

    with pytest.raises(TransactionError) as exc_info:
        Transactions(STAC_URL).delete_item("ws-test", "missing")

    assert exc_info.value.status_code == 404


@respx.mock
def test_add_item_body_url_error() -> None:
    body_url = "https://example.com/missing.geojson"
    respx.get(body_url).mock(return_value=httpx.Response(404, text="not found"))

    with pytest.raises(EoApiError) as exc_info:
        Transactions(STAC_URL).add_item("ws-test", body_url)

    assert exc_info.value.status_code == 404


@respx.mock
def test_delete_item_connection_error() -> None:
    respx.delete(f"{STAC_URL}/collections/ws-test/items/x").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(EoApiConnectionError):
        Transactions(STAC_URL).delete_item("ws-test", "x")


class _PystacLike:
    def to_dict(self) -> dict:
        return ITEM_JSON


@pytest.mark.parametrize("item", [ITEM_JSON, _PystacLike()], ids=["dict", "to_dict"])
@respx.mock
def test_add_item_from_object(item: object) -> None:
    route = respx.post(f"{STAC_URL}/collections/ws-test/items").mock(return_value=httpx.Response(201, json=ITEM_JSON))

    Transactions(STAC_URL).add_item("ws-test", item)

    assert json.loads(route.calls.last.request.content) == ITEM_JSON


@respx.mock
def test_update_item() -> None:
    url = f"{STAC_URL}/collections/ws-test/items/new-item"
    route = respx.put(url).mock(return_value=httpx.Response(200, json=ITEM_JSON))

    assert Transactions(STAC_URL).update_item("ws-test", ITEM_JSON)["id"] == "new-item"
    assert json.loads(route.calls.last.request.content) == ITEM_JSON


@respx.mock
def test_patch_item() -> None:
    url = f"{STAC_URL}/collections/ws-test/items/new-item"
    route = respx.patch(url).mock(return_value=httpx.Response(200, json=ITEM_JSON))

    Transactions(STAC_URL).patch_item("ws-test", "new-item", {"properties": {"a": 1}})

    request = route.calls.last.request
    assert request.headers["Content-Type"] == "application/merge-patch+json"
    assert json.loads(request.content) == {"properties": {"a": 1}}


@respx.mock
def test_collection_writes() -> None:
    collection = {"id": "c1", "type": "Collection"}
    add = respx.post(f"{STAC_URL}/collections").mock(return_value=httpx.Response(201, json=collection))
    put = respx.put(f"{STAC_URL}/collections/c1").mock(return_value=httpx.Response(200, json=collection))
    patch = respx.patch(f"{STAC_URL}/collections/c1").mock(return_value=httpx.Response(200, json=collection))
    delete = respx.delete(f"{STAC_URL}/collections/c1").mock(return_value=httpx.Response(204))
    tx = Transactions(STAC_URL)

    tx.add_collection(collection)
    tx.update_collection(collection)
    tx.patch_collection("c1", {"description": "d"})
    tx.delete_collection("c1")

    assert add.called and put.called and delete.called
    assert patch.calls.last.request.headers["Content-Type"] == "application/merge-patch+json"


@respx.mock
def test_bulk_add_items_chunks() -> None:
    route = respx.post(f"{STAC_URL}/collections/ws-test/bulk_items").mock(return_value=httpx.Response(200, json="ok"))
    items = [{**ITEM_JSON, "id": f"i{n}"} for n in range(5)]

    Transactions(STAC_URL).bulk_add_items("ws-test", items, method="upsert", chunk_size=2)

    bodies = [json.loads(call.request.content) for call in route.calls]
    assert [list(b["items"]) for b in bodies] == [["i0", "i1"], ["i2", "i3"], ["i4"]]
    assert {b["method"] for b in bodies} == {"upsert"}


@pytest.mark.parametrize(
    ("method", "path", "call"),
    [
        ("PUT", "/collections/ws-test/items/new-item", lambda tx: tx.update_item("ws-test", ITEM_JSON)),
        ("PATCH", "/collections/ws-test/items/new-item", lambda tx: tx.patch_item("ws-test", "new-item", {})),
        ("POST", "/collections/ws-test/bulk_items", lambda tx: tx.bulk_add_items("ws-test", [ITEM_JSON])),
        ("POST", "/collections", lambda tx: tx.add_collection({"id": "c1"})),
        ("DELETE", "/collections/c1", lambda tx: tx.delete_collection("c1")),
    ],
)
@respx.mock
def test_write_errors(method: str, path: str, call: object) -> None:
    respx.route(method=method, url=f"{STAC_URL}{path}").mock(return_value=httpx.Response(409, text="conflict"))

    with pytest.raises(TransactionError) as exc_info:
        call(Transactions(STAC_URL))  # type: ignore[operator]

    assert exc_info.value.status_code == 409
