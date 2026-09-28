"""Tests for the vector (tipg / OGC API - Features) client."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import requests

from eoapi_client import open_features

VECTOR_URL = "http://example.com/vector/"
LANDING = {"title": "tipg", "links": []}
COLLECTIONS = {"collections": [{"id": "public.my_data", "itemType": "feature"}]}


def _response(payload: dict, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload).encode()
    response.url = VECTOR_URL
    return response


@patch("owslib.ogcapi.http_get")
def test_open_features_forwards_headers(mock_get) -> None:
    mock_get.return_value = _response(LANDING)

    client = open_features(VECTOR_URL, headers={"Authorization": "Bearer token"})

    assert client.headers["Authorization"] == "Bearer token"

    mock_get.return_value = _response(COLLECTIONS)
    collections = client.collections()

    assert collections["collections"][0]["id"] == "public.my_data"
    assert mock_get.call_args.kwargs["headers"]["Authorization"] == "Bearer token"


@patch("owslib.ogcapi.http_get")
def test_open_features_cql2_filter_is_passthrough(mock_get) -> None:
    mock_get.return_value = _response(LANDING)
    client = open_features(VECTOR_URL)

    mock_get.return_value = _response({"type": "FeatureCollection", "features": []})
    client.collection_items("public.my_data", **{"filter": "ogc_fid = 3", "filter-lang": "cql2-text"})

    params = mock_get.call_args.kwargs["params"]
    assert params["filter"] == "ogc_fid = 3"
    assert params["filter-lang"] == "cql2-text"


@patch("owslib.ogcapi.http_get")
def test_open_features_error_has_no_status_code(mock_get) -> None:
    # Known OWSLib limitation: non-2xx responses raise a plain RuntimeError,
    # with no structured status code attached.
    mock_get.return_value = _response(LANDING)
    client = open_features(VECTOR_URL)

    mock_get.return_value = _response({"detail": "not found"}, status=404)
    with pytest.raises(RuntimeError, match="not found"):
        client.collection_items("public.does-not-exist")


def test_open_features_requires_owslib() -> None:
    with (
        patch.dict("sys.modules", {"owslib.ogcapi.features": None}),
        pytest.raises(ImportError, match=r"eoapi-client\[vector\]"),
    ):
        open_features(VECTOR_URL)
