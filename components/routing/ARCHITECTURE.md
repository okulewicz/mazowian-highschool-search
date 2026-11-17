# OpenTripPlanner routing process

Status: placeholder; no engine configuration, image, graph, or endpoint exists.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Run OpenTripPlanner **v2.10** using the downloader's GTFS and OSM snapshots.
Graph construction and serving are separate invocations of this component.
The frontend uses this component for travel estimates; it does not store user
projects. Do not introduce a second engine without owner approval.

## Inputs and outputs

- Build inputs: a validated `transport-data` snapshot manifest and its GTFS/OSM
  files, plus version-controlled OTP build/router configuration.
- Build output: a versioned graph associated with the exact input checksums,
  OTP version, and configuration. Activate only after a successful smoke test.
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
3. Add reproducible graph-build and serve commands, resource guidance,
   health/readiness checks, and safe graph replacement/rollback.
4. Configure frontend access, bounded queries, and logging without coordinates
   or home locations. Document GTFS validity and Europe/Warsaw time handling.

## Acceptance checks

Test a small permitted fixture graph, unsupported modes, no-route results,
invalid coordinates, service-date/timezone boundaries, unavailable graphs, and
failed rebuilds. Measure click-to-route latency against the owner's agreed
budget. Real regional graph builds belong outside routine pull-request CI.
