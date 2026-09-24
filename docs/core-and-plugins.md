# Core API and plugins

`portolan-cli` is the command-line interface for building, checking, and
publishing Portolan catalogs. It uses `portolan-python` for Portolan catalog
semantics where that library provides the needed API.

The CLI still owns data processing commands. Those commands create or transform
assets, call format-specific libraries, and write CLI-owned operational files.

## Core-backed behavior

These areas should use `portolan-python` instead of reimplementing catalog
semantics in the CLI:

- registry access;
- catalog, collection, item, asset, and link traversal;
- HREF resolution;
- STAC metadata detection;
- validation and conformance APIs when available;
- read-only inspection of Portolan metadata.

Current refactors route registry, inspect, README catalog reads, item traversal,
query helpers, logo catalog reads, and clean metadata detection through the core
API.

## CLI-owned behavior

These areas stay in `portolan-cli` unless a separate plugin design moves them:

- converting data into GeoParquet or COG;
- generating STAC GeoParquet mirrors;
- creating PMTiles, thumbnails, styles, and derived assets;
- extracting from ArcGIS, WFS, and CARTO;
- partitioning GeoParquet files;
- pushing, pulling, syncing, and cloning object storage content.

Those commands may write Portolan metadata after processing data. The metadata
semantics should still move toward `portolan-python` when a suitable API exists.

## Plugin boundary

`portolan-cli` discovers optional command plugins through the
`portolan.cli.plugins` entry point group.

`portolan-geoserver` uses that boundary to mount:

```bash
portolan geoserver plan ./catalog --offline
portolan geoserver publish ./catalog --workspace demo
portolan geoserver serve --catalog-id example-catalog --workspace demo
```

The plugin owns GeoServer behavior. `portolan-cli` only mounts the command group.

Future input or output integrations can use the same boundary when the project
is ready to split extractor or publisher code out of the CLI.
