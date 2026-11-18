# Transport data and map-tile processes

Status: the local map-tile batch process is implemented; no downloader or
scheduled refresh job exists yet.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Maintain fresh GTFS bus/other public-transport schedules and OSM street data for
the agreed Mazovian coverage. This is a containerized batch process, not the
routing engine. It does not scrape school websites or build the OTP graph.

## Inputs and outputs

- Inputs: approved GTFS provider URLs, OSM extract URL, coverage, refresh policy,
  and source licensing/attribution configuration.
- Outputs: immutable snapshot directories containing GTFS ZIPs, OSM PBF data,
  and a versioned manifest consumed by `routing`.
- Manifest: source URLs, retrieval timestamps, checksums, file sizes, feed
  validity periods, geographic coverage, and attribution. Never store secrets.
- Publish a current-snapshot pointer only after all required inputs validate.
  A failed or partial refresh must retain the previous usable snapshot.

## Map-tile generation process

Tile generation is a separate batch invocation within `transport-data`; it does
not download data, build an OTP graph, or select a tile host. It consumes a
local PBF and its source checksum, never the public OSM tile service.

Run from the repository root after Docker is installed and the versioned local
snapshot is available:

```sh
sha256sum /path/to/mazowieckie-latest.osm.pbf
python3 components/transport-data/tiles/generate.py \
  --input /path/to/mazowieckie-latest.osm.pbf \
  --input-sha256 <verified-pbf-sha256> \
  --source-url https://download.geofabrik.de/europe/poland/mazowieckie.html \
  --retrieved-at 2026-01-01T00:00:00Z \
  --output-root /path/to/map-tiles
```

The command runs Tilemaker v3.2.0 from its immutable container digest with
network access disabled. The checked-in `config.json` and `process.lua` produce
PMTiles v3 archives containing Mapbox Vector Tiles, zooms 5–14, and
`place`, `transportation`, `waterway`, `water`, `landuse`, and `building`
layers. The tile contents are renderer-neutral; the frontend supplies its map
style and can consume the PMTiles archive through a PMTiles-capable vector-tile
renderer.

Artifacts are written to `versions/<build-id>/map.pmtiles` with a
`manifest.json` recording source URL/retrieval time, input checksum, renderer
digest, configuration checksums, zooms, attribution, and output checksum.
`current` is an atomically replaced relative symlink to a complete version.
Failed generation leaves the previous pointer unchanged. Build IDs are derived
from the input, configuration, and renderer identity; an existing matching
version is checksum-verified before it can become current. Keep the output
directory out of Git.

The archive metadata carries linked OpenStreetMap contributor attribution and
Geofabrik processing credit; the frontend must also show attribution visibly
whenever the map is displayed. Record the Geofabrik source URL in the manifest.
Before any external tile/data publication, verify the current ODbL 1.0 and
Geofabrik attribution and redistribution terms for the actual output. This
process does not decide where/how the artifact is hosted.

## Implementation round

1. Confirm providers, permitted usage, coverage, and refresh cadence with owner.
2. Implement bounded downloads, conditional requests, retry/backoff, and source
   validation, including redirects, size limits, and safe ZIP handling.
3. Validate GTFS structure/service dates and OSM input suitability for OTP
   v2.10; report expired feeds and missing coverage explicitly.
4. Provide refresh and validation commands, container packaging, documented
   scheduling, and snapshot retention behavior.
5. Run map-tile generation independently against a validated local PBF
   snapshot; never trigger it as part of OTP graph construction.

## Acceptance checks

Use tiny synthetic/local fixtures for successful refresh, unchanged sources,
timeouts, corrupt archives, unsafe paths/URLs, expired feeds, and partial
failure. Verify atomic publication and last-known-good retention. A refresh
must not automatically interrupt the running routing engine. Test map-tile
checksum rejection, metadata, generated output, atomic current-pointer
replacement, and failed-generation retention without downloading regional data
in CI.
