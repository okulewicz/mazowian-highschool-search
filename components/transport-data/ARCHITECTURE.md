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
- Manifest: source URLs, retrieval timestamps, checksums, file sizes, feed
  validity periods, geographic coverage, and attribution. Never store secrets.
- Publish a current-snapshot pointer only after all required inputs validate.
  A failed or partial refresh must retain the previous usable snapshot.

## Implementation round

1. Confirm providers, permitted usage, coverage, and refresh cadence with owner.
2. Implement bounded downloads, conditional requests, retry/backoff, and source
   validation, including redirects, size limits, and safe ZIP handling.
3. Validate GTFS structure/service dates and OSM input suitability for OTP
   v2.10; report expired feeds and missing coverage explicitly.
4. Provide refresh and validation commands, container packaging, documented
   scheduling, and snapshot retention behavior.

## Acceptance checks

Use tiny synthetic/local fixtures for successful refresh, unchanged sources,
timeouts, corrupt archives, unsafe paths/URLs, expired feeds, and partial
failure. Verify atomic publication and last-known-good retention. A refresh
must not automatically interrupt the running routing engine.
