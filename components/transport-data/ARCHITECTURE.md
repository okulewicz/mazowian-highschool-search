# Transport data and map-tile processes

Status: a standard-library GTFS refresh command and local map-tile batch
process are implemented. OSM snapshot downloading, production packaging, and
scheduling remain unresolved.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Maintain fresh GTFS bus/other public-transport schedules and OSM street data for
the agreed Mazovian coverage. This is a containerized batch process, not the
routing engine. It does not scrape school websites or build the OTP graph.

## Inputs and outputs

- Inputs: the candidate source registry in `sources.json`. It lists Warsaw,
  WKD, and Polish Trains feeds, but owner approval for retrieval and snapshot
  publication is still pending. The Polish Trains feed covers Poland and is not
  limited to Mazowieckie. The registry does not resolve the main architecture's
  broader coverage question.
- Outputs: immutable snapshot directories under the configured output path,
  retaining each downloaded file separately with a versioned `manifest.json`.
  `current.json` points to the latest successfully published snapshot.
- The manifest records source URLs, per-source retrieval timestamps,
  SHA-256 checksums, byte sizes, static feed service-date ranges, realtime
  header timestamps/freshness, source terms, geographic coverage, and required
  attribution. The Warsaw static feed's upstream `attributions.txt` is retained
  in the raw ZIP, copied into the snapshot, and included verbatim in the
  manifest. Vehicle-position attribution uses the realtime `FeedHeader`
  timestamp and identifies Miasto Stołeczne Warszawa and
  `http://api.um.warszawa.pl`.
- Static feeds are required for publication; realtime feeds are optional.
  An unavailable or stale realtime file is recorded as such and does not
  invalidate valid static feeds. Static and realtime files remain distinct.
  The vehicle-position manifest notes that some `trip_id` values do not match
  static GTFS. Polish Trains realtime freshness is not inferred from retrieval
  time; stale or unknown source timestamps are surfaced.
- Redirects are restricted to HTTPS on `mkuran.pl`. Downloads have time,
  retry, and size bounds. Static archives are checked for required GTFS files,
  service dates, corruption, and unsafe member paths without extracting them.
- Publish `current.json` atomically only after all required static inputs
  validate. Failed refreshes leave the previous pointer and snapshot intact.
  Snapshots are retained; cleanup/retention scheduling is not implemented.
- `sources.json` records the candidate feed inventory and terms. All sources
  are disabled pending explicit owner approval; the refresh fails closed until
  the registry records approval and each downloaded source is individually
  approved. Confirm terms and redistribution permission before enabling feeds.

Run a refresh with:

```sh
python3 components/transport-data/refresh.py --output /path/to/transport-data
```

Run focused, fixture-only tests with:

```sh
python3 -m unittest discover -s components/transport-data/tests -v
```

The command currently publishes GTFS only; OSM data is not included in these
snapshots until its source, permission, and validation are implemented.

## Approved OSM source

Use the official Geofabrik [Mazowieckie extract page](https://download.geofabrik.de/europe/poland/mazowieckie.html)
and its [latest PBF](https://download.geofabrik.de/europe/poland/mazowieckie-latest.osm.pbf).
Coverage is Geofabrik's Mazowieckie regional extract; do not imply that it
includes neighboring regions or all cross-border travel.

Record the page URL and the direct PBF URL in each OSM manifest entry, along
with retrieval time (UTC), upstream data timestamp reported by Geofabrik (when
available), SHA-256, downloaded byte size, coverage, and schema version. The
upstream timestamp and size change over time and must be captured on refresh,
not checked in as fixed values. Treat the extract as OpenStreetMap data under
[ODbL 1.0](https://www.openstreetmap.org/copyright). Preserve credit to
OpenStreetMap contributors and Geofabrik's processing attribution (the
Geofabrik download server identifies data as processed by Geofabrik GmbH and
created by OpenStreetMap contributors). Before enabling external
redistribution, verify and satisfy ODbL attribution/share-alike requirements
and Geofabrik's applicable attribution terms.

Stream downloads to a size-limited temporary file with bounded timeouts and
retries. Validate the response, PBF readability, and checksum before placing
it in a new immutable snapshot. Publish by atomic rename/pointer update only
after every required input validates; on any failure, remove staging data and
leave the current snapshot unchanged. Keep PBFs and Snapshot/build artifacts
out of version control.

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

1. Confirm source usage/redistribution, coverage, and refresh cadence with the
   owner.
2. Implement Geofabrik OSM ingestion and manifest validation for OTP v2.10;
   do not commit PBFs or snapshots.
3. Package and schedule only after deployment and resource decisions.
4. Run map-tile generation independently against a validated local PBF
   snapshot; never trigger it as part of OTP graph construction.

## Acceptance checks

Test source metadata/attribution, stale or unavailable realtime data, corrupt
archives, unsafe paths/URLs, expired feeds, and partial failure with local
fixtures. Verify atomic snapshot publication and last-known-good retention.
Test tile checksum validation, metadata, output, atomic pointer replacement,
and failed-generation retention. CI must not download live feeds or regional
extracts.
