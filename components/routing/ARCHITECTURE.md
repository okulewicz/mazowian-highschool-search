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

## Acceptance checks

Test a small permitted fixture graph, unsupported modes, no-route results,
invalid coordinates, service-date/timezone boundaries, unavailable graphs, and
failed rebuilds. Measure click-to-route latency against the owner's agreed
budget. Real regional graph builds belong outside routine pull-request CI.
