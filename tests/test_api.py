"""Tests for the EoApi entry point and the shared client."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from eoapi_client import EoApi, __version__

BASE_URL = "https://example.com"
AUTH = {"Authorization": "Bearer token"}


@respx.mock
def test_default_service_urls() -> None:
    stac = respx.get(f"{BASE_URL}/stac/collections").mock(return_value=httpx.Response(200, json={"collections": []}))
    raster = respx.post(f"{BASE_URL}/raster/searches/register").mock(return_value=httpx.Response(200, json={"id": "abc"}))

    with EoApi(f"{BASE_URL}/") as api:
        api.stac.collections()
        api.raster.register_search({})

    assert stac.called and raster.called
    assert stac.calls.last.request.headers["User-Agent"] == f"eoapi-client/{__version__}"


@respx.mock
def test_service_url_overrides() -> None:
    route = respx.get("https://stac.other.com/v1/collections").mock(return_value=httpx.Response(200, json={}))

    with EoApi(BASE_URL, stac_url="https://stac.other.com/v1") as api:
        api.stac.collections()

    assert route.called


@respx.mock
def test_services_share_injected_client() -> None:
    respx.get(f"{BASE_URL}/stac/collections").mock(return_value=httpx.Response(200, json={}))
    raster = respx.post(f"{BASE_URL}/raster/searches/register").mock(return_value=httpx.Response(200, json={"id": "a"}))
    client = httpx.Client(headers={"X-Test": "1"})

    with EoApi(BASE_URL, client=client, headers=AUTH) as api:
        api.stac.collections()
        api.raster.register_search({})

    request = raster.calls.last.request
    assert request.headers["X-Test"] == "1"
    assert request.headers["Authorization"] == "Bearer token"
    assert not client.is_closed


def test_close_closes_own_client() -> None:
    api = EoApi(BASE_URL)
    api.close()
    assert api._client.is_closed


@respx.mock
def test_download_asset_foreign_host_gets_no_auth(tmp_path: Path) -> None:
    item = {"id": "i", "assets": {"data": {"href": "https://bucket.example.org/data.tif"}}}
    respx.get(f"{BASE_URL}/stac/collections/c/items/i").mock(return_value=httpx.Response(200, json=item))
    asset = respx.get("https://bucket.example.org/data.tif").mock(return_value=httpx.Response(200, content=b"x"))
    client = httpx.Client(headers={"Authorization": "Bearer client-default"})

    with EoApi(BASE_URL, client=client, headers=AUTH) as api:
        api.stac.download_asset("c", "i", "data", tmp_path / "data.tif")

    assert "Authorization" not in asset.calls.last.request.headers
