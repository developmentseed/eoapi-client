"""Python client for eoAPI."""

from importlib.metadata import version

from ._http import EoApiConnectionError, EoApiError
from .api import EoApi
from .raster import Raster
from .stac import AssetNotFoundError, Stac, UnsupportedAssetSchemeError, download_asset, list_collections
from .transactions import TransactionError, Transactions
from .vector import open_features

__version__ = version("eoapi-client")

__all__ = [
    "AssetNotFoundError",
    "EoApi",
    "EoApiConnectionError",
    "EoApiError",
    "Raster",
    "Stac",
    "TransactionError",
    "Transactions",
    "UnsupportedAssetSchemeError",
    "__version__",
    "download_asset",
    "list_collections",
    "open_features",
]
