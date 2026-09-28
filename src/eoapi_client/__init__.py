"""Python client for eoAPI."""

from importlib.metadata import version

from ._http import EoApiConnectionError, EoApiError
from .api import EoApi
from .auth import TokenAuth, client_credentials_auth, mock_oidc_auth
from .raster import Raster
from .stac import AssetNotFoundError, Stac, UnsupportedAssetSchemeError, download_asset, list_collections
from .transactions import TransactionError, Transactions
from .vector import VectorTiles, open_features

__version__ = version("eoapi-client")

__all__ = [
    "AssetNotFoundError",
    "EoApi",
    "EoApiConnectionError",
    "EoApiError",
    "Raster",
    "Stac",
    "TokenAuth",
    "TransactionError",
    "Transactions",
    "UnsupportedAssetSchemeError",
    "VectorTiles",
    "__version__",
    "client_credentials_auth",
    "download_asset",
    "list_collections",
    "mock_oidc_auth",
    "open_features",
]
