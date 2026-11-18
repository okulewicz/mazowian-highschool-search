# Transport data refresh process

Status: placeholder; no downloader or scheduled job exists yet.
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
- Manifest: source URLs, retrieval timestamps, upstream publication/data
  timestamps where available, SHA-256 checksums, byte sizes, feed validity
  periods, geographic coverage, licenses, and required attribution. Never
  store secrets.
- Publish a current-snapshot pointer only after all required inputs validate.
  A failed or partial refresh must retain the previous usable snapshot.

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

1. Confirm providers, permitted usage, coverage, and refresh cadence with owner.
2. Implement bounded downloads, conditional requests, retry/backoff, and source
   validation, including redirects, size limits, and safe ZIP handling. Enable
   the Geofabrik source above without committing its PBF or snapshot.
3. Validate GTFS structure/service dates and OSM input suitability for OTP
   v2.10; report expired feeds and missing coverage explicitly.
4. Provide refresh and validation commands, container packaging, documented
   scheduling, and snapshot retention behavior.

## Acceptance checks

Use tiny synthetic/local fixtures for successful refresh, unchanged sources,
timeouts, corrupt archives, unsafe paths/URLs, expired feeds, and partial
failure. Verify atomic publication and last-known-good retention. A refresh
must not automatically interrupt the running routing engine.
