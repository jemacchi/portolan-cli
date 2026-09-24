"""Tests that STAC-facing CLI code delegates to portolan-python."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from portolan_cli import inspect as inspect_module
from portolan_cli import readme as readme_module
from portolan_cli import stac_parquet

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class LinkStub:
    href: str
    raw: dict[str, Any]


def test_owned_item_hrefs_for_collection_uses_portolan_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []
    item_path = tmp_path / "items" / "road-a.json"
    item_path.parent.mkdir()
    item_path.write_text("{}", encoding="utf-8")

    class FakeCollection:
        @classmethod
        def open(cls, path: Path) -> FakeCollection:
            opened.append(path)
            return cls()

        def item_links(self) -> Iterator[LinkStub]:
            yield LinkStub(item_path.as_uri(), {"href": "./items/road-a.json"})

    monkeypatch.setattr(stac_parquet, "Collection", FakeCollection)
    collection_json = tmp_path / "collection.json"
    collection_json.write_text("{}", encoding="utf-8")

    assert stac_parquet.owned_item_hrefs(collection_json) == [
        ("./items/road-a.json", item_path)
    ]
    assert opened == [collection_json]


def test_owned_item_hrefs_for_catalog_uses_portolan_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []
    item_path = tmp_path / "root-item.json"
    item_path.write_text("{}", encoding="utf-8")

    class FakeCatalog:
        @classmethod
        def open(cls, path: Path) -> FakeCatalog:
            opened.append(path)
            return cls()

        def item_links(self) -> Iterator[LinkStub]:
            yield LinkStub(item_path.as_uri(), {"href": "./root-item.json"})

    monkeypatch.setattr(stac_parquet, "Catalog", FakeCatalog)
    catalog_json = tmp_path / "catalog.json"
    catalog_json.write_text("{}", encoding="utf-8")

    assert stac_parquet.owned_item_hrefs(catalog_json) == [("./root-item.json", item_path)]
    assert opened == [catalog_json]


def test_inspect_collection_uses_portolan_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []

    class FakeCollection:
        data = {
            "id": "roads",
            "title": "Roads",
            "description": "Road network",
            "extent": {"spatial": {"bbox": [[-71.0, -35.0, -70.0, -34.0]]}},
        }

        @classmethod
        def open(cls, path: Path) -> FakeCollection:
            opened.append(path)
            return cls()

    monkeypatch.setattr(inspect_module, "Collection", FakeCollection)
    monkeypatch.setattr(inspect_module, "count_items", lambda _path: 3)
    collection_dir = tmp_path / "roads"
    collection_dir.mkdir()
    collection_json = collection_dir / "collection.json"
    collection_json.write_text("{}", encoding="utf-8")

    result = inspect_module.inspect_collection(collection_dir)

    assert opened == [collection_json]
    assert result.collection_id == "roads"
    assert result.item_count == 3
    assert result.bbox == [-71.0, -35.0, -70.0, -34.0]


def test_inspect_catalog_uses_portolan_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []

    class FakeCollection:
        data = {"id": "roads"}

    class FakeCatalog:
        data = {"id": "demo", "description": "Demo catalog"}

        @classmethod
        def open(cls, path: Path) -> FakeCatalog:
            opened.append(path)
            return cls()

        def collections(self) -> Iterator[FakeCollection]:
            yield FakeCollection()
            yield FakeCollection()

    monkeypatch.setattr(inspect_module, "Catalog", FakeCatalog)
    catalog_json = tmp_path / "catalog.json"
    catalog_json.write_text("{}", encoding="utf-8")

    result = inspect_module.inspect_catalog(tmp_path)

    assert opened == [catalog_json]
    assert result.catalog_id == "demo"
    assert result.collection_count == 2


def test_read_item_uses_portolan_item(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opened: list[Path] = []

    class FakeItem:
        data = {"type": "Feature", "id": "road-a"}

        @classmethod
        def open(cls, path: Path) -> FakeItem:
            opened.append(path)
            return cls()

    monkeypatch.setattr(readme_module, "Item", FakeItem)
    item_path = tmp_path / "road-a.json"

    assert readme_module._read_item(item_path) == {"type": "Feature", "id": "road-a"}
    assert opened == [item_path]


def test_load_collection_stac_uses_portolan_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []

    class FakeCollection:
        data = {"type": "Collection", "id": "roads"}

        @classmethod
        def open(cls, path: Path) -> FakeCollection:
            opened.append(path)
            return cls()

    monkeypatch.setattr(readme_module, "Collection", FakeCollection)
    monkeypatch.setattr(readme_module, "owned_item_hrefs", lambda _path: [])
    collection_dir = tmp_path / "roads"
    collection_dir.mkdir()
    collection_json = collection_dir / "collection.json"
    collection_json.write_text("{}", encoding="utf-8")

    assert readme_module.load_collection_stac(collection_dir) == {
        "type": "Collection",
        "id": "roads",
    }
    assert opened == [collection_json]


def test_aggregate_catalog_extent_uses_portolan_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []

    class FakeCollection:
        href = "file:///catalog/roads/collection.json"
        data = {
            "id": "roads",
            "extent": {
                "spatial": {"bbox": [[-71.0, -35.0, -70.0, -34.0]]},
                "temporal": {"interval": [["2024-01-01T00:00:00Z", None]]},
            },
        }

    class FakeCatalog:
        @classmethod
        def open(cls, path: Path) -> FakeCatalog:
            opened.append(path)
            return cls()

        def collections(self) -> Iterator[FakeCollection]:
            yield FakeCollection()

    monkeypatch.setattr(readme_module, "Catalog", FakeCatalog)

    result = readme_module.aggregate_catalog_extent(tmp_path)

    assert opened == [tmp_path]
    assert result == {
        "bbox": [-71.0, -35.0, -70.0, -34.0],
        "temporal_start": "2024-01-01T00:00:00Z",
        "temporal_end": None,
        "collections": ["roads"],
    }


def test_aggregate_catalog_extent_fallback_uses_portolan_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    catalog_opened: list[Path] = []
    collection_opened: list[Path] = []

    class FakeCatalog:
        @classmethod
        def open(cls, path: Path) -> FakeCatalog:
            catalog_opened.append(path)
            return cls()

        def collections(self) -> Iterator[Any]:
            return iter(())

    class FakeCollection:
        href = "file:///catalog/roads/collection.json"
        data = {
            "id": "roads",
            "extent": {
                "spatial": {"bbox": [[-71.0, -35.0, -70.0, -34.0]]},
                "temporal": {"interval": [[None, None]]},
            },
        }

        @classmethod
        def open(cls, path: Path) -> FakeCollection:
            collection_opened.append(path)
            return cls()

    monkeypatch.setattr(readme_module, "Catalog", FakeCatalog)
    monkeypatch.setattr(readme_module, "Collection", FakeCollection)
    collection_dir = tmp_path / "roads"
    collection_dir.mkdir()
    collection_json = collection_dir / "collection.json"
    collection_json.write_text("{}", encoding="utf-8")

    result = readme_module.aggregate_catalog_extent(tmp_path)

    assert catalog_opened == [tmp_path]
    assert collection_opened == [collection_json]
    assert result["collections"] == ["roads"]


def test_generate_catalog_readme_uses_portolan_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened: list[Path] = []

    class FakeCatalog:
        data = {"id": "demo", "title": "Demo catalog", "description": "From catalog"}

        @classmethod
        def open(cls, path: Path) -> FakeCatalog:
            opened.append(path)
            return cls()

    monkeypatch.setattr(readme_module, "Catalog", FakeCatalog)
    monkeypatch.setattr(
        readme_module,
        "load_merged_metadata",
        lambda _path, _root: {},
    )
    monkeypatch.setattr(
        readme_module,
        "aggregate_catalog_extent",
        lambda _path: {
            "bbox": None,
            "temporal_start": None,
            "temporal_end": None,
            "collections": [],
        },
    )
    (tmp_path / "catalog.json").write_text("{}", encoding="utf-8")

    readme = readme_module.generate_catalog_readme(tmp_path)

    assert opened == [tmp_path / "catalog.json"]
    assert readme.startswith("# Demo catalog\n\nFrom catalog")
