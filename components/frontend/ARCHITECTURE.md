# Browser-local school comparison frontend

Status: placeholder; no frontend application or serving process exists yet.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Provide school selection/comparison projects, JSON import/export, simple map
visualization, and fast routing between a clicked home point and school.
Serve a static client application and catalog artifacts from this component.
No project backend, accounts, or server-side project storage.

## Inputs and outputs

- Inputs: versioned discovery/details/ranking artifacts and the documented
  OTP v2.10 routing interface. Join catalogs on stable `school_id`.
- Project: `schema_version`, school/profile comparison entries, home point,
  comparison and travel preferences. Each entry references a `school_id` and
  profile/program identity (or unresolved raw profile text). Multiple profiles
  at one school must remain separate choices. Define migration/version
  compatibility at implementation.
- Private annotations: reviewer labels, opinions, preference/fallback notes,
  and manual overrides with provenance. These belong only to the project;
  never upload them to shared school catalogs or telemetry.
- Show open-door events and important admissions deadlines with event venues,
  admission cycles, source links, precision, and update/cancellation status
  alongside non-point requirements, profile/threshold, ranking, and fee data.
  Keep upcoming and historical dates distinct and flag stale/uncertain notices.
- Keep user-entered transit/bike/mixed travel estimates and route notes
  distinguishable from computed OTP results. Preserve uncertain raw values;
  never silently replace a manual estimate with a computed duration.
- Persistence: browser-local storage only, plus user-triggered JSON files.
  Document whether home location is included in exports after owner decision.
- Display source years/editions, stale data, and unknown fields. Historical
  cutoffs and rankings are context, not admission predictions.

## Implementation round

1. Scaffold a TypeScript client with the chosen ecosystem's standard tooling;
   define project schema and catalog/routing fixtures before integrations.
2. Add create/edit/delete projects, school selection/comparison, browser
   persistence, and validated import/export. Imported files are data, not code.
3. Add a map with clickable school and home points, travel mode/time controls,
   route geometry, and duration. Provide a usable non-map selection alternative.
4. Cancel obsolete routing requests and ignore stale responses when clicks
   change. Show loading, no-route, error, and unsupported-mode states.
5. Add a static serving container, focused CI checks, and attribution. Disclose
   coordinate transmission to routing/map/geocoding services; never send whole
   projects or store home points in telemetry, server logs, or shared caches.

## Acceptance checks

Test project export/import round trips, reload persistence, invalid/oversized
JSON, unsupported schema versions, removed school IDs, storage failure, and
explicit deletion. Validate coordinates and never render imported raw HTML.
Use synthetic report-like fixtures for multiple profiles at one school,
private reviewer notes, partial addresses, unknown/approximate ranking and fee
values, open days without a year, and `HH:MM`/`HH:MM:SS` duration estimates.
Cover upcoming/past deadlines, profile-specific dates, changed/cancelled events,
and uncertain dates without presenting them as confirmed current deadlines.
Spreadsheet/TSV ingestion is an open owner decision, not an implemented import.
Test rapid repeated clicks, stale responses, routing outages, missing rankings,
and keyboard-accessible comparison. No network request may upload a project;
do not claim offline operation merely because storage is local.
