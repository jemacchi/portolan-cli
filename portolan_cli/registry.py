"""Compatibility boundary for Portolan registry APIs.

The implementation lives in ``portolan-python``. This module keeps the CLI's
registry command and tests pointed at a stable local boundary.
"""

from __future__ import annotations

from portolan import (
    DEFAULT_REGISTRY_URL,
    RegistryCatalogEntry,
    download_registry_catalog,
    load_registry_entries,
)

__all__ = [
    "DEFAULT_REGISTRY_URL",
    "RegistryCatalogEntry",
    "download_registry_catalog",
    "load_registry_entries",
]
