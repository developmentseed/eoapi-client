"""Python client for eoAPI."""

from importlib.metadata import version

from .transactions import TransactionError, Transactions

__version__ = version("eoapi-client")

__all__ = ["TransactionError", "Transactions", "__version__"]
