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
leave the current snapshot unchanged. Keep PBFs and snapshot/build artifacts
out of version control.

## Implementation round

1. Confirm provider usage, redistribution, coverage, and refresh cadence with
   the owner.
2. Implement bounded conditional requests and improved freshness policies where
   the upstream feeds support them.
3. Implement OSM ingestion and validation for OTP v2.10 using the source above,
   without committing PBFs or snapshots.
4. Add container packaging, documented scheduling, and snapshot retention
   behavior.

## Acceptance checks

Use tiny synthetic/local fixtures for source metadata and attribution, stale or
unavailable realtime data, corrupt archives, unsafe paths/URLs, expired feeds,
and partial failure. Verify atomic publication and last-known-good retention.
A refresh must not automatically interrupt the running routing engine. CI must
not download the live feeds.
