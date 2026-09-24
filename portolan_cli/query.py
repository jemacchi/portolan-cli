"""Catalog query API: list items, get item info, freshness checks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from portolan import Asset, AssetFormat, Catalog, Collection, Item

from portolan_cli.constants import (
    MTIME_TOLERANCE_SECONDS,
)
from portolan_cli.formats import (
    FormatType,
)
from portolan_cli.sync.checksums import compute_checksum, compute_dir_checksum
from portolan_cli.versions import (
    read_versions,
)

logger = logging.getLogger(__name__)


@dataclass
class ItemInfo:
    """Information about an item in the catalog.

    Attributes:
        item_id: STAC item identifier.
        collection_id: Parent collection identifier.
        format_type: Vector or raster format.
        bbox: Bounding box [min_x, min_y, max_x, max_y].
        asset_paths: Paths to data assets.
        title: Optional display title.
        description: Optional description.
        datetime: Acquisition/creation datetime.
    """

    item_id: str
    collection_id: str
    format_type: FormatType
    bbox: list[float]
    asset_paths: list[str] = field(default_factory=list)
    title: str | None = None
    description: str | None = None
    datetime: datetime | None = None


def list_items(
    catalog_root: Path,
    collection_id: str | None = None,
) -> list[ItemInfo]:
    """List items in a Portolan catalog.

    Args:
        catalog_root: Root directory of the catalog.
        collection_id: Optional collection to filter by.

    Returns:
        List of ItemInfo objects.
    """
    catalog_path = catalog_root / "catalog.json"
    if not catalog_path.exists():
        return []

    items: list[ItemInfo] = []
    for collection in _iter_catalog_collections(catalog_root):
        col_id = _collection_id(collection)
        if collection_id and collection_id not in {col_id, _collection_dir_name(collection)}:
            continue
        for item in _collection_items(collection):
            items.append(_item_info(item, col_id))

    return items


def get_item_info(
    catalog_root: Path,
    stac_id: str,
) -> ItemInfo:
    """Get information about a specific item.

    Args:
        catalog_root: Root directory of the catalog.
        stac_id: STAC identifier in format "collection/item".

    Returns:
        ItemInfo for the requested item.

    Raises:
        KeyError: If the item doesn't exist.
    """
    if "/" not in stac_id:
        raise KeyError(f"Item not found: {stac_id} (expected format: collection/item)")

    collection_id, item_id = stac_id.split("/", 1)

    collection_path = catalog_root / collection_id / "collection.json"
    if collection_path.exists():
        try:
            collection = Collection.open(collection_path)
            for item in _collection_items(collection):
                if item.id == item_id:
                    return _item_info(item, collection_id)
        except (OSError, TypeError, ValueError):
            pass

    item_path = catalog_root / collection_id / item_id / f"{item_id}.json"
    if item_path.exists():
        try:
            return _item_info(Item.open(item_path), collection_id)
        except (OSError, TypeError, ValueError):
            pass

    raise KeyError(f"Item not found: {stac_id}")


def _iter_catalog_collections(catalog_root: Path) -> list[Collection]:
    try:
        collections = list(Catalog.open(catalog_root).collections())
    except (OSError, TypeError, ValueError):
        collections = []

    seen = {_collection_json_path(collection) for collection in collections}
    for child in sorted(catalog_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        collection_json = child / "collection.json"
        if collection_json in seen or not collection_json.exists():
            continue
        try:
            collections.append(Collection.open(collection_json))
        except (OSError, TypeError, ValueError):
            continue
    return collections


def _collection_items(collection: Collection) -> list[Item]:
    items: list[Item] = []
    for link in collection.item_links():
        try:
            item = Item.open(link.href)
        except (OSError, TypeError, ValueError):
            continue
        if item.data.get("type") == "Feature":
            items.append(item)
    return items


def _collection_id(collection: Collection) -> str:
    return collection.id or _collection_dir_name(collection)


def _collection_dir_name(collection: Collection) -> str:
    path = _href_to_path(collection.href)
    if path is not None:
        return path.parent.name
    return collection.id


def _collection_json_path(collection: Collection) -> Path | None:
    return _href_to_path(collection.href)


def _href_to_path(href: str) -> Path | None:
    parsed = urlparse(href)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme:
        return None
    return Path(href)


def _item_info(item: Item, collection_id: str) -> ItemInfo:
    data = item.data
    properties = data.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    bbox = data.get("bbox")
    if not isinstance(bbox, list):
        bbox = [0, 0, 0, 0]
    assets = list(item.assets())
    return ItemInfo(
        item_id=item.id,
        collection_id=collection_id,
        format_type=_format_type(assets),
        bbox=bbox,
        asset_paths=[href for asset in assets if isinstance(href := asset.raw.get("href"), str)],
        title=properties.get("title") if isinstance(properties.get("title"), str) else None,
        description=properties.get("description")
        if isinstance(properties.get("description"), str)
        else None,
    )


def _format_type(assets: list[Asset]) -> FormatType:
    formats = {asset.format for asset in assets}
    if AssetFormat.COG in formats:
        return FormatType.RASTER
    if AssetFormat.GEOPARQUET in formats:
        return FormatType.VECTOR
    return FormatType.UNKNOWN


def is_current(
    path: Path,
    versions_path: Path,
    *,
    asset_key: str | None = None,
) -> bool:
    """Check if a file is unchanged compared to versions.json.

    Uses mtime as fast-path, falls back to sha256 if mtime changed.

    Args:
        path: Path to the file to check.
        versions_path: Path to versions.json for this collection.
        asset_key: Optional explicit key to look up in versions.json.
            If not provided, looks up by filename alone (legacy behavior).

    Returns:
        True if file is unchanged (already tracked at current state),
        False if new or modified.
    """
    if not versions_path.exists():
        return False

    versions_file = read_versions(versions_path)
    if not versions_file.versions:
        return False

    current_version = versions_file.versions[-1]

    # Look for this file in current version assets
    # Try explicit key first, then item-scoped key, then filename, then converted name
    asset = None
    filename = path.name

    if asset_key is not None:
        asset = current_version.assets.get(asset_key)

    if asset is None:
        # Try item-scoped key format: {item_id}/{filename}
        # This is how _update_versions stores multi-asset items
        item_id = path.parent.name
        item_scoped_key = f"{item_id}/{filename}"
        asset = current_version.assets.get(item_scoped_key)

    if asset is None:
        # Try bare filename (legacy format)
        asset = current_version.assets.get(filename)

    if asset is None:
        # Also check for stem.parquet (converted name)
        parquet_name = f"{path.stem}.parquet"
        asset = current_version.assets.get(parquet_name)

    if asset is None:
        # Try item-scoped with converted name
        item_id = path.parent.name
        item_scoped_parquet = f"{item_id}/{parquet_name}"
        asset = current_version.assets.get(item_scoped_parquet)

    if asset is None:
        return False

    # Get file stats once (used for both mtime and size checks)
    file_stat = path.stat()

    # For directory-format assets (e.g., FileGDB), skip the mtime fast-path and
    # size comparison — neither is reliable for directories. A directory's mtime
    # changes when its children change, but MTIME_TOLERANCE_SECONDS (2s, for
    # NFS/CIFS compatibility) would mask rapid modifications. Instead, go
    # directly to the content fingerprint (compute_dir_checksum), which hashes
    # the sorted (path, size, mtime) tuples of all files inside the directory.
    if path.is_dir():
        current_checksum = compute_dir_checksum(path)
        return current_checksum == asset.sha256

    # Fast path: mtime unchanged AND size unchanged → file is current
    # Both conditions must hold; size check catches fast overwrites within mtime tolerance
    mtime_unchanged = (
        asset.mtime is not None and abs(file_stat.st_mtime - asset.mtime) < MTIME_TOLERANCE_SECONDS
    )
    size_unchanged = asset.size_bytes is not None and file_stat.st_size == asset.size_bytes

    if mtime_unchanged and size_unchanged:
        return True

    # Medium path: size differs → definitely changed
    if asset.size_bytes is not None and file_stat.st_size != asset.size_bytes:
        return False

    # Slow path: mtime changed but size matches → check sha256
    current_checksum = compute_checksum(path)
    return current_checksum == asset.sha256
