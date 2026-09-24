"""CLI command plugin discovery tests."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import click
import pytest
from click.testing import CliRunner

from portolan_cli.plugins import load_cli_plugins

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class Plugin:
    name: str
    command_path: tuple[str, ...]
    command: click.Command


def _command(message: str) -> click.Command:
    @click.command()
    def command() -> None:
        click.echo(message)

    return command


def _entry_point(name: str, plugin: Plugin) -> MagicMock:
    entry_point = MagicMock()
    entry_point.name = name
    entry_point.load.return_value = lambda: plugin
    return entry_point


def test_load_cli_plugins_mounts_entry_point_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    root = click.Group("portolan")
    plugin = Plugin("geoserver", ("geoserver",), _command("served"))
    entry_point = _entry_point("geoserver", plugin)
    monkeypatch.setattr("portolan_cli.plugins.entry_points", lambda group: [entry_point])

    load_cli_plugins(root)
    result = CliRunner().invoke(root, ["geoserver"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "served"
    entry_point.load.assert_called_once()


def test_load_cli_plugins_honors_enabled_plugin_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = click.Group("portolan")
    geoserver = _entry_point("geoserver", Plugin("geoserver", ("geoserver",), _command("geo")))
    other = _entry_point("other", Plugin("other", ("other",), _command("other")))
    monkeypatch.setenv("PORTOLAN_CLI_PLUGINS", "geoserver")
    monkeypatch.setattr("portolan_cli.plugins.entry_points", lambda group: [geoserver, other])

    load_cli_plugins(root)

    assert "geoserver" in root.commands
    assert "other" not in root.commands


def test_load_cli_plugins_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    root = click.Group("portolan")
    geoserver = _entry_point("geoserver", Plugin("geoserver", ("geoserver",), _command("geo")))
    monkeypatch.setenv("PORTOLAN_CLI_PLUGINS", "none")
    monkeypatch.setattr("portolan_cli.plugins.entry_points", lambda group: [geoserver])

    load_cli_plugins(root)

    assert root.commands == {}


def test_load_cli_plugins_mounts_nested_command_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = click.Group("portolan")
    export = click.Group("export")
    root.add_command(export, "export")
    plugin = Plugin("geoserver", ("export", "geoserver"), _command("nested"))
    monkeypatch.setattr("portolan_cli.plugins.entry_points", lambda group: [_entry_point("geo", plugin)])

    load_cli_plugins(root)
    result = CliRunner().invoke(root, ["export", "geoserver"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "nested"


def test_load_cli_plugins_skips_command_collisions(monkeypatch: pytest.MonkeyPatch) -> None:
    root = click.Group("portolan")
    root.add_command(_command("builtin"), "geoserver")
    plugin = Plugin("geoserver", ("geoserver",), _command("plugin"))
    monkeypatch.setattr("portolan_cli.plugins.entry_points", lambda group: [_entry_point("geo", plugin)])

    load_cli_plugins(root)
    result = CliRunner().invoke(root, ["geoserver"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "builtin"


def test_load_cli_plugins_ignores_broken_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    root = click.Group("portolan")
    broken = MagicMock()
    broken.name = "broken"
    broken.load.side_effect = RuntimeError("boom")
    monkeypatch.setattr("portolan_cli.plugins.entry_points", lambda group: [broken])

    load_cli_plugins(root)

    assert root.commands == {}
