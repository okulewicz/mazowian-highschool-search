# School website and location discovery process

Status: placeholder; no discovery code or catalog exists yet.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Discover high schools in the agreed coverage, their official websites, and
locations. This is a containerized extraction process. Profile/admission/fee
parsing belongs to `school-details`, rankings to `school-rankings`.

## Inputs and outputs

- Inputs: owner-approved school registry/source exports, coverage/school-type
  filters, and any approved geocoding configuration.
- Output: versioned base school catalog for details, rankings, and frontend.
- Each record: stable `school_id`, source identifiers, official name, aliases,
  website URL, address, WGS84 latitude/longitude when known, and provenance.
- Preserve unresolved websites/locations as unknown with diagnostic status;
  do not invent coordinates or identify schools solely by normalized names.

## Implementation round

1. Confirm authoritative sources, school types, coverage, and permitted usage.
2. Define the shared school identity/schema contract with its consumers.
3. Extract and normalize records, deduplicate by authoritative identifiers,
   validate URLs and coordinates, and record uncertain matches for review.
4. Provide an idempotent extraction command, container, versioned artifacts,
   and documented correction/reconciliation behavior across refreshes.

## Acceptance checks

Fixture tests cover Polish diacritics, duplicate names at different addresses,
renamed schools, missing websites, ambiguous geocoding, out-of-coverage records,
and stable IDs across repeated runs. Validate discovered URLs before fetching;
honor source/geocoder rate limits and licenses.
