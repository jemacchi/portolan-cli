# Portolan CLI

[![PyPI version](https://badge.fury.io/py/portolan-cli.svg)](https://badge.fury.io/py/portolan-cli)
[![CI](https://github.com/portolan-sdi/portolan-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/portolan-sdi/portolan-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/portolan-sdi/portolan-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/portolan-sdi/portolan-cli)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/portolan-sdi/portolan-cli/blob/main/LICENSE)

Portolan is an opinionated specification for serverless spatial data infrastructures.
It defines how publishers store, organize, document, and serve geospatial data as static files in their own storage.
Every Portolan catalog should offer a predictable, high-quality experience for publishers, people, and agents.

Portolan builds on existing standards instead of replacing them.
GeoParquet and PMTiles serve vector data, while COG serves raster data.
STAC provides a consistent catalog structure and index.
Required README and AGENTS.md files explain each catalog to people and agents.
The specification also covers operational details such as spatial ordering, bounding boxes, and CORS.

This repository contains the Portolan CLI, an implementation of the specification.
It helps publishers:

- Build [STAC](https://stacspec.org/en/) catalogs with [GeoParquet](https://geoparquet.org/) and [COG](https://cogeo.org/) assets.
- Extract ArcGIS, WFS, and Carto sources.
- Inspect and fetch published catalogs from the Portolan registry.
- Generate thumbnails, [PMTiles](https://docs.protomaps.com/pmtiles/), MapLibre styles, and STAC GeoParquet indexes.
- Track collection versions and checksums without a database.
- Validate catalog metadata, structure, and assets against the [Portolan specification](https://github.com/portolan-sdi/portolan-spec).
- Push, pull, sync, and clone catalogs through S3, GCS, Azure, or S3-compatible storage.
- Use structured JSON output, a typed Python API, or backend plugins.

## Command Areas

The core commands build and publish a static Portolan catalog:

```sh
portolan init ./catalog
portolan add ./source-files --portolan-dir ./catalog
portolan check ./catalog --strict
portolan push s3://my-bucket/catalog --catalog ./catalog
```

The extraction commands turn service data into the same catalog shape:

```sh
portolan extract arcgis URL ./catalog --auto
portolan extract wfs URL ./catalog --auto
portolan extract carto URL ./catalog --auto
```

The registry commands read the published Portolan registry.
They can list registered catalogs and fetch local snapshots for follow-on work:

```sh
portolan registry list
portolan registry fetch CATALOG_ID --output ./catalogs
```

## Installation

*Portolan CLI is pre-1.0 software, as breaking changes are expected for the time being.*

```sh
uv tool install portolan-cli
```

Or with pip:

```sh
pip install portolan-cli
```

## Documentation

Start with the [end-to-end publishing example](https://portolan-sdi.github.io/portolan-cli/examples/).
We plan to add more tutorials over time.

See the [full documentation](https://portolan-sdi.github.io/portolan-cli/).
It includes an auto-generated [CLI reference](https://portolan-sdi.github.io/portolan-cli/reference/cli/)
and [Python API reference](https://portolan-sdi.github.io/portolan-cli/reference/python/).
The [core API and plugins guide](https://portolan-sdi.github.io/portolan-cli/core-and-plugins/)
explains which
behavior belongs in `portolan-python`, which behavior stays in the CLI, and how
optional command plugins are mounted.

## Development

```sh
git clone https://github.com/portolan-sdi/portolan-cli.git
cd portolan-cli
uv sync --all-extras
uv run pytest
```

See the [contributing guide](https://portolan-sdi.github.io/portolan-cli/contributing/) for details.

## License

[Apache 2.0](https://github.com/portolan-sdi/portolan-cli/blob/main/LICENSE)
