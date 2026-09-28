"""Tests for TokenAuth and its token fetchers."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from eoapi_client import EoApi, EoApiError, TokenAuth, client_credentials_auth, mock_oidc_auth

BASE_URL = "https://example.com"
COLLECTIONS_URL = f"{BASE_URL}/stac/collections"


def _jwt(exp: float) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"header.{payload}.sig"


class _Fetch:
    def __init__(self, *tokens: str) -> None:
        self.tokens = list(tokens)
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        return self.tokens.pop(0) if len(self.tokens) > 1 else self.tokens[0]


@respx.mock
def test_token_attached_and_cached() -> None:
    route = respx.get(COLLECTIONS_URL).mock(return_value=httpx.Response(200, json={}))
    token = _jwt(time.time() + 900)
    fetch = _Fetch(token)

    with EoApi(BASE_URL, auth=TokenAuth(fetch)) as api:
        api.stac.collections()
        api.stac.collections()

    assert route.calls.last.request.headers["Authorization"] == f"Bearer {token}"
    assert fetch.calls == 1


@respx.mock
def test_token_refetched_near_expiry() -> None:
    respx.get(COLLECTIONS_URL).mock(return_value=httpx.Response(200, json={}))
    fetch = _Fetch(_jwt(time.time() + 10))

    with EoApi(BASE_URL, auth=TokenAuth(fetch)) as api:
        api.stac.collections()
        api.stac.collections()

    assert fetch.calls == 2


@respx.mock
def test_opaque_token_cached() -> None:
    respx.get(COLLECTIONS_URL).mock(return_value=httpx.Response(200, json={}))
    fetch = _Fetch("opaque")

    with EoApi(BASE_URL, auth=TokenAuth(fetch)) as api:
        api.stac.collections()
        api.stac.collections()

    assert fetch.calls == 1


@respx.mock
def test_401_refetches_and_retries_with_body() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.headers["Authorization"] == "Bearer stale":
            return httpx.Response(401)
        return httpx.Response(201, json=json.loads(request.content))

    route = respx.post(COLLECTIONS_URL).mock(side_effect=respond)

    with EoApi(BASE_URL, auth=TokenAuth(_Fetch("stale", "fresh"))) as api:
        created = api.transactions.add_collection({"id": "c1"})

    assert created == {"id": "c1"}
    assert route.call_count == 2


@respx.mock
def test_second_401_raises() -> None:
    respx.get(COLLECTIONS_URL).mock(return_value=httpx.Response(401, text="nope"))

    with EoApi(BASE_URL, auth=TokenAuth(_Fetch("a", "b"))) as api, pytest.raises(EoApiError) as exc_info:
        api.stac.collections()

    assert exc_info.value.status_code == 401


@respx.mock
def test_client_credentials_auth() -> None:
    token_url = "https://keycloak.example.com/realms/eoapi/protocol/openid-connect/token"
    token_route = respx.post(token_url).mock(return_value=httpx.Response(200, json={"access_token": "kc-token"}))

    assert client_credentials_auth(token_url, "cid", "secret", scope="stac:write").token() == "kc-token"
    form = parse_qs(token_route.calls.last.request.content.decode())
    assert form == {
        "grant_type": ["client_credentials"],
        "client_id": ["cid"],
        "client_secret": ["secret"],
        "scope": ["stac:write"],
    }


@respx.mock
def test_client_credentials_auth_error() -> None:
    token_url = "https://keycloak.example.com/token"
    respx.post(token_url).mock(return_value=httpx.Response(401, json={"error": "invalid_client"}))

    with pytest.raises(EoApiError) as exc_info:
        client_credentials_auth(token_url, "cid", "wrong").token()

    assert exc_info.value.status_code == 401


@respx.mock
def test_mock_oidc_auth() -> None:
    route = respx.post(f"{BASE_URL}/mock-oidc/").mock(return_value=httpx.Response(200, json={"token": "mock-token"}))

    assert mock_oidc_auth(f"{BASE_URL}/mock-oidc", username="u", scopes="openid").token() == "mock-token"
    request = route.calls.last.request
    assert request.headers["Accept"] == "application/json"
    assert parse_qs(request.content.decode()) == {"username": ["u"], "scopes": ["openid"]}


@respx.mock
def test_download_asset_foreign_host_gets_no_token(tmp_path: Path) -> None:
    item = {"id": "i", "assets": {"data": {"href": "https://bucket.example.org/data.tif"}}}
    respx.get(f"{COLLECTIONS_URL}/c/items/i").mock(return_value=httpx.Response(200, json=item))
    asset = respx.get("https://bucket.example.org/data.tif").mock(return_value=httpx.Response(200, content=b"x"))

    with EoApi(BASE_URL, auth=TokenAuth(_Fetch("secret"))) as api:
        api.stac.download_asset("c", "i", "data", tmp_path / "data.tif")

    assert "Authorization" not in asset.calls.last.request.headers


def test_vector_gets_current_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr("eoapi_client.api.open_features", lambda url, headers: captured.update(headers))

    EoApi(BASE_URL, auth=TokenAuth(_Fetch("vector-token"))).vector()

    assert captured["Authorization"] == "Bearer vector-token"
