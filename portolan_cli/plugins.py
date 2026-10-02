"""Click command plugin discovery for portolan-cli."""

from __future__ import annotations

import logging
import os
from importlib.metadata import entry_points
from typing import Any

import click

PLUGIN_ENTRY_POINT_GROUP = "portolan.cli.plugins"
PLUGIN_ENV_VAR = "PORTOLAN_CLI_PLUGINS"

logger = logging.getLogger(__name__)


def load_cli_plugins(root: click.Group) -> None:
    """Mount installed command plugins onto the root CLI group."""
    for entry_point in entry_points(group=PLUGIN_ENTRY_POINT_GROUP):
        if not _is_enabled(entry_point.name):
            continue
        try:
            plugin = entry_point.load()()
            _mount_plugin(root, plugin, entry_point.name)
        except Exception as exc:  # pragma: no cover - defensive import boundary
            logger.warning("Failed to load CLI plugin %s: %s", entry_point.name, exc)


def _mount_plugin(root: click.Group, plugin: object, entry_point_name: str) -> None:
    name = _plugin_name(plugin, entry_point_name)
    if not _is_enabled(name):
        return
    command = getattr(plugin, "command", None)
    command_path = getattr(plugin, "command_path", (name,))
    if not isinstance(command, click.Command):
        raise TypeError(f"CLI plugin {name!r} must expose a Click command")
    if not _valid_command_path(command_path):
        raise TypeError(f"CLI plugin {name!r} must expose a non-empty command_path")
    _add_command_path(root, tuple(command_path), command)


def _add_command_path(
    root: click.Group, command_path: tuple[str, ...], command: click.Command
) -> None:
    current = root
    for part in command_path[:-1]:
        next_command = current.commands.get(part)
        if not isinstance(next_command, click.Group):
            raise click.ClickException(
                f"Cannot mount plugin at {' '.join(command_path)}: {part} is not a group"
            )
        current = next_command
    command_name = command_path[-1]
    if command_name in current.commands:
        logger.warning("Skipping CLI plugin command %s; command already exists", command_name)
        return
    current.add_command(command, command_name)


def _plugin_name(plugin: object, entry_point_name: str) -> str:
    name = getattr(plugin, "name", entry_point_name)
    return name if isinstance(name, str) and name else entry_point_name


def _valid_command_path(value: Any) -> bool:
    return (
        isinstance(value, tuple)
        and len(value) > 0
        and all(isinstance(part, str) and part for part in value)
    )


def _is_enabled(name: str) -> bool:
    raw = os.environ.get(PLUGIN_ENV_VAR)
    if raw is None or raw.strip().lower() == "all":
        return True
    enabled = _enabled_names(raw)
    if "none" in enabled:
        return False
    return name in enabled


def _enabled_names(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}
