"""Portolan registry command tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError

import pytest
from click.testing import CliRunner

from portolan_cli.cli import cli
from portolan_cli.registry import RegistryCatalogEntry

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_cli_registry_list_outputs_online_catalogs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "portolan_cli.registry.load_registry_entries",
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


def test_cli_registry_list_outputs_json(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = RegistryCatalogEntry(
        id="catalog-a",
        url="https://example.test/a/catalog.json",
        title="Catalog A",
        status="valid",
    )
    monkeypatch.setattr(
        "portolan_cli.registry.load_registry_entries",
        lambda *args, **kwargs: [entry],
    )

    result = CliRunner().invoke(cli, ["registry", "list", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["catalogs"] == [
        {
            "id": "catalog-a",
            "url": "https://example.test/a/catalog.json",
            "title": "Catalog A",
            "status": "valid",
        }
    ]


@pytest.mark.parametrize(
    "failure",
    [
        URLError("connection refused"),
        ValueError("Registry URL must use HTTP or HTTPS"),
        TypeError("Expected JSON object"),
    ],
)
def test_cli_registry_list_reports_registry_failures(
    failure: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> list[RegistryCatalogEntry]:
        raise failure

    monkeypatch.setattr("portolan_cli.registry.load_registry_entries", fail)

    result = CliRunner().invoke(cli, ["registry", "list"])

    assert result.exit_code == 1
    assert f"Could not load Portolan registry: {failure}" in result.output


def test_cli_registry_list_reports_registry_failure_as_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> list[RegistryCatalogEntry]:
        raise ValueError("invalid registry URL")

    monkeypatch.setattr("portolan_cli.registry.load_registry_entries", fail)

    result = CliRunner().invoke(cli, ["registry", "list", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "success": False,
        "command": "registry list",
        "data": {},
        "errors": [
            {
                "type": "ValueError",
                "message": "Could not load Portolan registry: invalid registry URL",
            }
        ],
    }


def test_cli_registry_fetch_outputs_catalog_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "portolan_cli.registry.load_registry_entries",
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
        "portolan_cli.registry.download_registry_catalog",
        lambda catalog_url, output_dir, **kwargs: tmp_path / "catalog-a",
    )

    result = CliRunner().invoke(
        cli,
        ["registry", "fetch", "catalog-a", "--output", str(tmp_path), "--path-only"],
    )

    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(tmp_path / "catalog-a")


def test_cli_registry_fetch_reports_download_failure_as_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "portolan_cli.registry.load_registry_entries",
        lambda *args, **kwargs: [
            RegistryCatalogEntry(
                id="catalog-a",
                url="https://example.test/a/catalog.json",
                status="valid",
            )
        ],
    )

    def fail(catalog_url: str, output_dir: Path, **kwargs: object) -> Path:
        raise HTTPError(catalog_url, 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr("portolan_cli.registry.download_registry_catalog", fail)

    result = CliRunner().invoke(
        cli,
        [
            "registry",
            "fetch",
            "catalog-a",
            "--output",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "success": False,
        "command": "registry fetch",
        "data": {},
        "errors": [
            {
                "type": "HTTPError",
                "message": "Could not download catalog 'catalog-a': HTTP Error 404: Not Found",
            }
        ],
    }


def test_cli_registry_fetch_reports_registry_failure_as_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> list[RegistryCatalogEntry]:
        raise ValueError("invalid registry response")

    monkeypatch.setattr("portolan_cli.registry.load_registry_entries", fail)

    result = CliRunner().invoke(cli, ["registry", "fetch", "catalog-a", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output)["errors"][0] == {
        "type": "ValueError",
        "message": "Could not load Portolan registry: invalid registry response",
    }


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["registry", "fetch", "missing"], "Catalog not found in registry: missing"),
        (["registry", "fetch", "--all"], "No catalogs found in registry."),
    ],
)
def test_cli_registry_fetch_reports_empty_registry(
    arguments: list[str],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "portolan_cli.registry.load_registry_entries",
        lambda *args, **kwargs: [],
    )

    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code == 1
    assert message in result.output


def test_cli_registry_fetch_outputs_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = RegistryCatalogEntry(
        id="catalog-a",
        url="https://example.test/a/catalog.json",
        status="valid",
    )
    catalog_root = tmp_path / "catalog-a"
    monkeypatch.setattr(
        "portolan_cli.registry.load_registry_entries",
        lambda *args, **kwargs: [entry],
    )
    monkeypatch.setattr(
        "portolan_cli.registry.download_registry_catalog",
        lambda *args, **kwargs: catalog_root,
    )

    result = CliRunner().invoke(
        cli,
        ["registry", "fetch", "catalog-a", "--output", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["catalogs"] == [
        {
            "id": "catalog-a",
            "url": "https://example.test/a/catalog.json",
            "path": str(catalog_root),
        }
    ]


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
        "portolan_cli.registry.load_registry_entries",
        lambda *args, **kwargs: entries,
    )
    monkeypatch.setattr(
        "portolan_cli.registry.download_registry_catalog",
        lambda catalog_url, output_dir, **kwargs: output_dir / catalog_url.split("/")[-2],
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


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["registry", "fetch"], "Provide CATALOG_ID or use --all."),
        (
            ["registry", "fetch", "catalog-a", "--all"],
            "Use either CATALOG_ID or --all, not both.",
        ),
    ],
)
def test_cli_registry_fetch_rejects_invalid_selection(arguments: list[str], message: str) -> None:
    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code == 1
    assert message in result.output
