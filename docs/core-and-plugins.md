# Core API and plugins

`portolan-cli` uses `portolan-python` for Portolan catalog semantics. The core
library provides the catalog model, link traversal, registry access, and STAC
metadata detection used by the CLI.

The CLI keeps its operational features. Format conversion, extraction,
thumbnails, object storage, and derived assets depend on tools and workflows
that are outside the core library.

## Install a command plugin

An installed package can add a Click command through the
`portolan.cli.plugins` entry point group. The CLI loads all available plugins
by default.

For example, install `portolan-geoserver` in the same environment:

```bash
pip install portolan-cli portolan-geoserver
portolan geoserver --help
```

The plugin supplies the complete `geoserver` command group. The CLI only
discovers and mounts it.

## Select plugins

Set `PORTOLAN_CLI_PLUGINS` to a comma-separated list when an environment has
several plugins but must load only some of them:

```bash
PORTOLAN_CLI_PLUGINS=geoserver portolan --help
```

Set the variable to `none` to disable command plugins:

```bash
PORTOLAN_CLI_PLUGINS=none portolan --help
```

## Use the GeoServer plugin

These commands come from `portolan-geoserver`. They become available under the
main CLI after that package is installed:

```bash
portolan geoserver plan ./catalog --offline
portolan geoserver publish ./catalog --workspace demo
portolan geoserver sync ./catalog --workspace demo
portolan geoserver serve --catalog-id example-catalog --workspace demo
```

The standalone `portolan-geoserver` executable exposes the same subcommands.
GeoServer publication remains in the plugin and is not part of
`portolan-python`.

## Provide a plugin

A plugin entry point must load a zero-argument factory. The factory returns an
object with these attributes:

| Attribute | Value |
|---|---|
| `name` | Plugin name used by `PORTOLAN_CLI_PLUGINS`. |
| `command_path` | Non-empty tuple that identifies the mount location. |
| `command` | Click command or group to mount. |

Register the factory in `pyproject.toml`:

```toml
[project.entry-points."portolan.cli.plugins"]
example = "example_package.plugin:get_portolan_cli_plugin"
```

The loader skips a plugin command when its mount location already contains a
command with the same name. A broken plugin does not prevent the base CLI from
starting; the loader records a warning instead.
