# Transport data refresh process

Status: local refresh container implemented; production scheduling and source
approval for redistribution remain unresolved.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Maintain fresh GTFS bus/other public-transport schedules and OSM street data for
the agreed Mazovian coverage. This is a containerized batch process, not the
routing engine. It does not scrape school websites or build the OTP graph.

## Inputs and outputs

- Inputs: static GTFS URLs in `sources.json` from the Kuran index and the
  Geofabrik Mazowieckie OSM PBF URL. Refresh is an explicit Docker Compose job.
- Outputs: immutable snapshot directories containing GTFS ZIPs, OSM PBF data,
  and a versioned manifest consumed by `routing`.
- Manifest: source and final URLs, retrieval timestamps, checksums, file sizes,
  GTFS service-date bounds, license, attribution, and validation status. The
  manifest schema does not yet include Geofabrik's upstream data timestamp or
  explicit coverage metadata. The input list covers static schedules only;
  realtime endpoints are separate and are not downloaded.
- The process checks HTTPS redirect hosts, applies timeouts and limited retry,
  bounds download and archive expansion sizes, validates ZIP contents and the
  PBF header, and publishes a `current` symlink only after all sources validate.
  A failed or partial refresh retains the previous snapshot.

Run locally with:

```sh
docker compose --profile jobs build transport-data
docker compose --profile jobs run --rm transport-data
```

Snapshots are written to ignored `.data/transport/`. The command does not build
or activate an OTP graph. Source terms and attribution are recorded in
`sources.json`; review the upstream terms before redistributing snapshots.
There is no configured staleness threshold because refresh cadence is still an
owner decision. Feed service-date bounds are recorded to expose expired feeds.

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
leave the current snapshot unchanged. Keep PBFs and snapshot/build artifacts
out of version control.

## Implementation round

1. Confirm permitted use/redistribution and refresh cadence with owner.
2. Extend manifest/source validation to record Geofabrik's upstream timestamp
   and declared coverage; add fixture checks for redirect limits, corrupt or
   oversized inputs, invalid service dates, and partial refreshes.
3. Add source-specific freshness reporting and retention policy after owner
   decisions.

## Acceptance checks

Use tiny synthetic/local fixtures for successful refresh, unchanged sources,
timeouts, corrupt archives, unsafe paths/URLs, expired feeds, and partial
failure. Verify atomic publication and last-known-good retention. A refresh
must not automatically interrupt the running routing engine.
