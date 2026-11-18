# Transport data refresh process

Status: a standard-library GTFS refresh command is implemented for the
mkuran.pl Warsaw, WKD, and Polish Trains feeds. OSM refresh, container
packaging, and scheduling are not implemented.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Maintain fresh GTFS bus/other public-transport schedules and OSM street data for
the agreed Mazovian coverage. This is a containerized batch process, not the
routing engine. It does not scrape school websites or build the OTP graph.

## Inputs and outputs

- Inputs: the source registry in `sources.json`; the current refresh includes
  the Warsaw, WKD, and Polish Trains feeds listed there. The Polish Trains feed
  covers Poland and is not limited to Mazowieckie.
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
- `sources.json` records the issue-approved feed inventory and terms. It does
  not resolve the main architecture's open question about overall coverage or
  future provider approval.

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

## Implementation round

1. Implement bounded conditional requests and improved freshness policies where
   the upstream feeds support them.
2. Implement OSM ingestion and validation for OTP v2.10.
3. Add container packaging, documented scheduling, and snapshot retention
   behavior.

## Acceptance checks

Use tiny synthetic/local fixtures for source metadata and attribution, stale or
unavailable realtime data, corrupt archives, unsafe paths/URLs, expired feeds,
and partial failure. Verify atomic publication and last-known-good retention.
A refresh must not automatically interrupt the running routing engine. CI must
not download the live feeds.
