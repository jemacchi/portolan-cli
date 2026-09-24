"""Portolan registry CLI command tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from portolan import RegistryCatalogEntry

from portolan_cli.cli import cli

pytestmark = pytest.mark.unit


def test_cli_registry_list_outputs_online_catalogs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "portolan.load_registry_entries",
        lambda *args, **kwargs: [
            RegistryCatalogEntry(
                id="catalog-a",
                url="https://example.test/a/catalog.json",
                title="Catalog A",
                status="valid",
            )
        ],
    )

    result = CliRunner().invoke(cli, ["registry", "list"])

    assert result.exit_code == 0, result.output
    assert "catalog-a" in result.output
    assert "https://example.test/a/catalog.json" in result.output


def test_cli_registry_fetch_outputs_catalog_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "portolan.load_registry_entries",
        lambda *args, **kwargs: [
            RegistryCatalogEntry(
                id="catalog-a",
                url="https://example.test/a/catalog.json",
                title="Catalog A",
                status="valid",
            )
        ],
    )
    monkeypatch.setattr(
        "portolan.download_registry_catalog",
        lambda catalog_url, output_dir: tmp_path / "catalog-a",
    )

    result = CliRunner().invoke(
        cli,
        ["registry", "fetch", "catalog-a", "--output", str(tmp_path), "--path-only"],
    )

    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(tmp_path / "catalog-a")


def test_cli_registry_fetch_all_outputs_all_catalog_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = [
        RegistryCatalogEntry(
            id="catalog-a",
            url="https://example.test/a/catalog.json",
            title="Catalog A",
            status="valid",
        ),
        RegistryCatalogEntry(
            id="catalog-b",
            url="https://example.test/b/catalog.json",
            title="Catalog B",
            status="valid",
        ),
    ]
    monkeypatch.setattr(
        "portolan.load_registry_entries",
        lambda *args, **kwargs: entries,
    )
    monkeypatch.setattr(
        "portolan.download_registry_catalog",
        lambda catalog_url, output_dir: output_dir / catalog_url.split("/")[-2],
    )

    result = CliRunner().invoke(
        cli,
        ["registry", "fetch", "--all", "--output", str(tmp_path), "--path-only"],
    )

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        str(tmp_path / "a"),
        str(tmp_path / "b"),
    ]
