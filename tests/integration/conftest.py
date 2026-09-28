"""Fixtures for tests against a live eoapi-k8s deployment.

Only collected when `EOAPI_URL` is set, e.g.
`EOAPI_URL=http://localhost uv run pytest tests/integration`.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from eoapi_client import EoApi, EoApiError

if not os.getenv("EOAPI_URL"):
    collect_ignore_glob = ["test_*.py"]

SAMPLE_COLLECTION = "noaa-emergency-response"


@pytest.fixture(scope="session")
def eoapi_url() -> str:
    return os.environ["EOAPI_URL"].rstrip("/")


@pytest.fixture(scope="session")
def auth(eoapi_url: str) -> dict[str, str]:
    """A bearer token from eoapi-k8s's mock OIDC server."""
    oidc_url = os.getenv("MOCK_OIDC_URL", f"{eoapi_url}/mock-oidc")
    response = httpx.post(
        f"{oidc_url}/",
        data={"username": "eoapi-client-it", "scopes": "openid"},
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture(scope="session")
def api(eoapi_url: str, auth: dict[str, str]) -> Iterator[EoApi]:
    with EoApi(eoapi_url, headers=auth) as api:
        yield api


@pytest.fixture(scope="session")
def sample_item(api: EoApi) -> dict[str, Any]:
    """The first sample item with assets (eoapi-k8s's own auth tests leave asset-less `test-*` items)."""
    return next(item for item in api.stac.iter_items(SAMPLE_COLLECTION, limit=50) if item["assets"])


@pytest.fixture
def new_item(api: EoApi, sample_item: dict[str, Any], tmp_path: Path) -> Iterator[Path]:
    """A copy of the sample item under a unique id, as a JSON file; deleted afterwards."""
    item = {**sample_item, "id": f"eoapi-client-it-{uuid.uuid4().hex[:8]}", "links": []}
    path = tmp_path / "item.json"
    path.write_text(json.dumps(item))
    yield path
    try:
        api.transactions.delete_item(SAMPLE_COLLECTION, item["id"])
    except EoApiError as exc:
        if exc.status_code != 404:
            raise
