# OpenTripPlanner routing process

Status: local OTP 2.10 graph build, smoke-test, activation, and serving process
implemented. Mode-specific routing verification and production deployment are
still outstanding.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Run OpenTripPlanner **v2.10** using the downloader's GTFS and OSM snapshots.
Graph construction and serving are separate invocations of this component.
The frontend uses this component for travel estimates; it does not store user
projects. Do not introduce a second engine without owner approval.

## Inputs and outputs

- Build inputs: `.data/transport/current` with a valid snapshot manifest and
  checksummed GTFS/OSM files. The host command runs the build inside the pinned
  OTP container.
- Build output: a versioned graph associated with the exact input checksums,
  OTP image digest, and recorded invocation/configuration checksum. The graph
  is smoke-tested against the v2.10 GTFS GraphQL endpoint before atomically
  updating `.data/routing/active`.
- Retained OTP build caches are performance aids, not graph artifacts. Keep them
  separate from published graphs and associate them with the exact OTP version,
  build-configuration checksum, and input checksums from the manifest. Cache
  reuse and invalidation are not implemented by the current build command.
- Query inputs: origin/destination coordinates, departure or arrival time,
  timezone, and supported mode/accessibility preferences.
- Query outputs: duration, legs/modes, transfers, geometry, and clear no-route
  or unavailable-data states. Document the concrete v2.10 API for the frontend.

## Implementation round

1. Verify [versioned OTP documentation](https://docs.opentripplanner.org/en/v2.10.0/)
   and pin an available v2.10 release/image and digest; do not use `latest`.
2. Prove walking, bike, transit, and mixed-mode support with a small graph.
   Explicitly verify car-only versus car/transit support. Escalate unsupported
   product requirements to the owner rather than treating them as implemented.
3. `python3 components/routing/build_graph.py .data` verifies source checksums,
   builds in a temporary directory, smoke-tests, and activates only on success.
   `docker compose up otp` serves the active graph separately on port 8080.
4. The GTFS GraphQL endpoint is `/otp/gtfs/v1`. The build smoke query only
   proves endpoint readiness; it does not yet prove route modes or the
   frontend query contract.

The pinned image is
`opentripplanner/opentripplanner:2.10.0@sha256:8d54e5c589186707ee365417f2202dc878c451fa3001b8edff07019531100933`.
The smoke check is not a claim that car-only, park-and-ride, or other mixed
modes are verified. No custom routing proxy or coordinate-redacting access-log
layer exists yet; do not enable request-body/debug logging or expose the
development endpoint publicly. Query bounds, Europe/Warsaw edge cases, no-route
semantics, stale realtime, and unavailable-graph responses still need focused
fixture verification.

## OTP v2.10 graph-build reuse

The [OTP v2.10 build documentation](https://docs.opentripplanner.org/en/v2.10.0/BuildConfiguration/)
documents two opt-in caches for expensive tasks: elevation profiles and
visibility graphs. They skip matching sub-computations on later builds, but do
not cache the OSM import or resulting street graph. They are disabled by default.

OTP also supports coarse whole-street-graph reuse: `--buildStreet` builds and
writes `streetGraph.obj` from OSM/DEM, and `--loadStreet` loads that artifact
while building transit data on top. This avoids repeating OSM/DEM street
construction for a GTFS-only rebuild, but is not partitioned or automatically
invalidated by OTP. It is the supported reuse strategy for an unchanged
street-network input; it is not incremental OSM graph building.

Keep `streetGraph.obj` and cache files separate from the published graph, and
associate each with a sidecar recording the exact OTP version, street-build
configuration checksum, OSM checksum, and DEM checksum (where used). Before
`--loadStreet`, require all those fingerprints to match; OTP does not enforce
them. Rebuild the street graph if OSM, DEM, relevant configuration, or OTP
version changes. A GTFS-only change can load the matching street graph, but
still requires building and validating a new complete graph. Bind each
published graph to the exact checksums of all its inputs.

For the task caches, use only the controls documented for the pinned OTP v2.10
release and retain cache metadata with OTP version, build-configuration
checksum, and exact inputs used. OTP's versioned cache format handles internal
serialization changes. Elevation entries are keyed by edge geometry and
visibility entries by OSM entity IDs and polygon coordinates, so changed
features miss while compatible unchanged entries may be reused. A replacement
DEM requires invalidating the elevation cache because its sampled values are
not represented by edge geometry. OTP prunes removed entries and does not
require manual invalidation of the visibility cache.

The current build command does not use a retained street graph or task caches.
Before implementing reuse, verify it with local synthetic OSM, DEM, and GTFS
fixtures and pinned OTP v2.10: build and save `streetGraph.obj`, then load it
for a GTFS-only rebuild; change the OSM fixture and confirm the sidecar check
forces a street-graph rebuild. Also verify task-cache reuse on an identical
build and invalidation after relevant OSM/DEM changes. CI must use only these
small local fixtures, never the regional extract. No cache-hit experiment is
claimed.

## Acceptance checks

Test a small permitted fixture graph, unsupported modes, no-route results,
invalid coordinates, service-date/timezone boundaries, unavailable graphs, and
failed rebuilds. Measure click-to-route latency against the owner's agreed
budget. Confirm street-graph reuse and invalidation with the local experiment
above before claiming cache reuse.
Real regional graph builds belong outside routine pull-request CI.
