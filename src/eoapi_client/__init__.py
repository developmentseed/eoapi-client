"""Python client for eoAPI."""

from importlib.metadata import version

from ._http import EoApiError
from .assets import AssetNotFoundError, UnsupportedAssetSchemeError, download_asset
from .collections import list_collections
from .raster import Raster
from .transactions import TransactionError, Transactions

__version__ = version("eoapi-client")

__all__ = [
    "AssetNotFoundError",
    "EoApiError",
    "Raster",
    "TransactionError",
    "Transactions",
    "UnsupportedAssetSchemeError",
    "__version__",
    "download_asset",
    "list_collections",
]
