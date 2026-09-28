"""`EoApi`: one entry point per eoAPI deployment."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from eoapi_client._http import DEFAULT_TIMEOUT, ClientOwner
from eoapi_client.raster import Raster
from eoapi_client.stac import Stac
from eoapi_client.transactions import Transactions
from eoapi_client.vector import open_features

if TYPE_CHECKING:
    from owslib.ogcapi.features import Features


class EoApi(ClientOwner):
    """All services of one eoAPI deployment, sharing one `httpx.Client`.

    Service URLs default to eoapi-k8s's ingress paths under `base_url`
    (`/stac`, `/raster`, `/vector`); pass `stac_url=` etc. to override any
    of them with an absolute URL.
    """

    def __init__(
        self,
        base_url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
        stac_url: str | None = None,
        raster_url: str | None = None,
        vector_url: str | None = None,
    ) -> None:
        super().__init__(client, timeout)
        base = base_url.rstrip("/")
        self._headers = headers or {}
        self._vector_url = vector_url or f"{base}/vector"
        stac_url = stac_url or f"{base}/stac"
        self.stac = Stac(stac_url, client=self._client, headers=headers)
        self.transactions = Transactions(stac_url, client=self._client, headers=headers)
        self.raster = Raster(raster_url or f"{base}/raster", client=self._client, headers=headers)

    def vector(self) -> Features:
        """Open an OWSLib `Features` client (see `open_features`); it doesn't share this client."""
        return open_features(self._vector_url, headers=self._headers)
