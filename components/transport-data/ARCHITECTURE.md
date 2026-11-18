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
  input list covers static schedules only; realtime endpoints are separate and
  are not downloaded.
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

## Implementation round

1. Confirm coverage, permitted use/redistribution, and refresh cadence with owner.
2. Add fixture checks for URL redirects, corrupt/oversized archives, invalid
    service dates, and partial refreshes.
3. Add source-specific freshness reporting and retention policy after owner
    decisions.

## Acceptance checks

Use tiny synthetic/local fixtures for successful refresh, unchanged sources,
timeouts, corrupt archives, unsafe paths/URLs, expired feeds, and partial
failure. Verify atomic publication and last-known-good retention. A refresh
must not automatically interrupt the running routing engine.
