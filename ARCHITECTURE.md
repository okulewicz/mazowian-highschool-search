# Architecture and implementation map

## Status and decision ownership

This is a scaffold for a Mazovian high school comparison proof of concept.
Nothing described below is implemented yet. Each component's
`ARCHITECTURE.md` is input for a separate Copilot implementation round.

The repository owner controls architecture boundaries: components, their
responsibilities, product scope, and where user data may live. Copilot chooses
technical implementation details within those boundaries. Do not silently add
services, merge components, introduce server-side project storage, or resolve
the open product/design questions below on the owner's behalf.

## Owner-defined components

| Component / designated process | Responsibility | Brief |
| --- | --- | --- |
| `transport-data` | Maintain fresh Mazovian GTFS schedules and OSM street data | [Brief](components/transport-data/ARCHITECTURE.md) |
| `routing` | OpenTripPlanner v2.10 graph building and route estimation | [Brief](components/routing/ARCHITECTURE.md) |
| `school-discovery` | Extract high school websites and locations | [Brief](components/school-discovery/ARCHITECTURE.md) |
| `school-details` | Parse class profiles, admission exam points, private-school fees, open days, and important deadlines | [Brief](components/school-details/ARCHITECTURE.md) |
| `school-rankings` | Import high school rankings from Perspektywy | [Brief](components/school-rankings/ARCHITECTURE.md) |
| `frontend` | Local-only comparison projects, import/export, map, and fast route interaction | [Brief](components/frontend/ARCHITECTURE.md) |

Batch jobs count as components; they do not need always-on HTTP servers.
Package each implemented component as a container or document its designated
process. Do not add pretend Dockerfiles or successful no-op service commands
before there is an implementation to run.

## Intended data flow

```text
GTFS sources + OSM --> transport-data --> versioned transport snapshots
                                                 |
                                                 v
                                      routing (OTP v2.10)
                                                 ^
                                                 | route requests
School sources --> school-discovery --> school-details
                         |                   |
Perspektywy --> school-rankings               |
                         |                   |
                         +-- school catalog artifacts --> frontend
```

School discovery also supplies the base catalog directly to the frontend.
The frontend joins discovery, details, and rankings using stable school IDs;
missing details or rankings must not hide a discovered school. Serve catalog
artifacts as static files with the frontend; a new catalog API service is not
part of this scaffold. The routing component exposes its routing interface.

## Technical defaults for implementation rounds

These are starting choices, not implemented dependencies:

- Ollama is assumed available throughout the infrastructure as a shared
  capability, not a seventh product component. Processes may use it for
  extraction/normalization; no separate model-hosting implementation is needed
  in this scaffold. Configure endpoint and model at deployment time.
- Python for download/extraction batch processes; TypeScript for the frontend.
  Select frameworks and lock dependencies only in the relevant implementation.
- Versioned JSON artifacts for school data and manifests. Retain raw transport
  files separately. Use UTF-8, ISO 8601 timestamps, and WGS84 coordinates.
- Every school record uses a stable `school_id`; prefer an authoritative ID,
  never a name alone. Store source identifiers and aliases for reconciliation.
- Discovery records contain name, website URL, address, location, and provenance.
  Details and rankings reference that ID rather than duplicating identities.
- Include `schema_version`, source URL, retrieval time, and applicable school
  year/ranking edition on published artifacts or their records. Record source
  publication dates where available; retrieval time is not publication time.
- Use explicit currency and billing period for fees, admission year and class
  profile for point thresholds, and edition/category for rankings. Missing
  values are unknown, not zero. Historical thresholds are not admission promises.
- Publish validated snapshots atomically, retaining the last known good data.
  A job must fail visibly rather than replacing good data with an empty result.
- Local development should eventually use Docker Compose for implemented
  processes, explicit refresh jobs, and a separately invoked OTP graph build.
  Production hosting and scheduling remain owner decisions.

Specify concrete schemas, commands, container configuration, and fixture-based
tests in the implementation PR that first produces each artifact. Coordinate
contract changes with its consumers; do not build all six components at once.

## Comparison model informed by the sample report

The supplied informal report is a requirements example, not a verified public
dataset. Do not commit its personal comments or use them as public test data.
Use synthetic examples when implementing these cases:

- A comparison entry identifies a school **and a particular profile/program**.
  Several entries may share one school without becoming duplicate schools.
  Keep liceum/technikum programs distinct even when they share an institution.
- Public catalog facts and private project annotations are separate. Reviewer
  labels, free-text opinions, preferences, and fallback choices stay in the
  browser-local project and its explicit exports, never in catalog artifacts.
- Open days can have an exact date/time and venue, an approximate month/range,
  or a raw note. Do not infer a year or reuse the school address as event venue.
- The details process must also discover and extract important deadlines from
  approved school/admissions sources: applications, exams/interviews, portfolio
  submission, document delivery, and enrollment confirmation where applicable.
  Associate events/deadlines with school, optional profile, and admission cycle;
  retain source, precision, timezone, and changed/cancelled status when stated.
  Keep historical notices distinct from upcoming dates. The frontend displays
  these dates and flags incomplete or stale information rather than guessing.
- Admission requirements include non-point criteria, such as a portfolio or
  language certificate, and source links. Preserve raw text alongside any
  structured interpretation; links are not themselves a numeric threshold.
- Incomplete addresses and profile URLs require later reconciliation, not
  invented coordinates or profile names.
- Blank cells, `???`, and `N/D` remain unknown with their original context.
  Approximate ranking notes must not become an exact official rank; unqualified
  tuition amounts must not acquire an assumed currency or billing period.
- Manual transit, bike, and mixed-mode time estimates remain separate from
  computed itineraries. Preserve the original value and route note, and record
  provenance and uncertainty. Parse `HH:MM` and `HH:MM:SS` explicitly into a
  duration, not a time of day; do not invent missing origins or departure times.

## Routing and privacy boundaries

Target OpenTripPlanner **v2.10**, with GTFS and OSM from `transport-data`.
Walking, cycling, car, and mixed public-transport journeys are product goals.
Verify mode support and API semantics against that version before promising
any combination, especially car-only routing versus park-and-ride. Do not
silently substitute another routing engine if a requested mode is unsupported.

Comparison projects, selected schools, home location, and preferences are
stored only in the browser, with explicit JSON import/export. No accounts,
server-side project persistence, or analytics containing project/location data.
Routing requests necessarily reveal their coordinates to the routing server;
map tiles or geocoders may reveal location too. Document these disclosures and
avoid recording coordinates in application/access logs. Local-only storage
does not imply fully offline or network-private operation.

## Ingestion and implementation safeguards

- Confirm source terms, robots policies, licensing, attribution, and permitted
  redistribution before enabling downloads or scraping. Do not bypass access
  controls or assume permission to scrape Perspektywy.
- Use configurable approved sources, timeouts, retry limits, request pacing,
  download size limits, and caching. Validate redirects and discovered URLs;
  block private/internal network targets and unsafe archive extraction.
- Treat scraped HTML and imported project JSON as untrusted. Do not render
  arbitrary HTML, execute imported content, or fetch URLs supplied by a project.
- Ollama-assisted extraction must treat source pages as untrusted data, not
  instructions. Require schema-validated output and supporting source evidence;
  a model must not invent dates, ranks, fees, thresholds, or school matches.
  Record model/prompt versions and extraction uncertainty. Bound requests and
  handle unavailable models/timeouts explicitly without publishing guessed data.
- Send only necessary public source content to Ollama. Never send browser-local
  projects, reviewer notes, home locations, or credentials. Do not expose the
  infrastructure's model endpoint directly to the frontend.
- Keep secrets, downloaded datasets, OTP graphs, and personal project exports
  out of version control. CI must use synthetic fixtures, not live scraping.

## Open questions for the owner

Record answers here before implementing behavior that depends on them.
Technical details within the agreed boundaries remain Copilot's responsibility.

| Question | Status / owner answer |
| --- | --- |
| Does coverage mean all Mazowieckie schools, only Warsaw, or also cross-border commutes and neighboring transport feeds? | Open |
| Which school types are included: licea, technika, vocational, public, private? | Open |
| Which official school registry and GTFS providers may be used, and is their data redistributable? | Open |
| What data refresh cadence and maximum acceptable staleness are needed? | Open |
| Does “car” require car-only routes, park-and-ride, drop-off, or all of these? If OTP v2.10 cannot meet a requirement, what architecture change is acceptable? | Open |
| Which mixed modes, departure/arrival times, accessibility needs, and acceptable routing latency should the comparison support? | Open |
| Which admission years, point types, class profiles, and fee periods should be compared? | Open |
| Should initial scope include pasting/importing spreadsheets or TSV like the sample, or only versioned project JSON? | Open |
| Should reviewer preferences remain free text or support structured labels? | Open |
| Which official admissions-calendar sources supplement school sites, and are reminders/calendar exports needed beyond displaying open days and deadlines? | Open |
| Which Perspektywy editions/categories are needed, and is automated extraction/republication permitted or should an approved manual import be used? | Open |
| Which map tile/geocoding provider and licensing/privacy trade-offs are acceptable? | Open |
| Is a home point allowed to be sent to a hosted routing service, and should it be included in exported projects by default? | Open |
| Is browser-local storage sufficient, or must the app also work offline? What project-size limits are expected? | Open |
| Where will public catalogs, routing, refresh jobs, and graph builds be hosted, and with what resource budget? | Open |

## Suggested implementation order

1. Confirm coverage, sources, licensing, and the routing-mode requirements.
2. Implement discovery and transport refresh independently with fixture tests.
3. Implement details and ranking imports against the discovery ID contract.
4. Build and validate an OTP v2.10 graph from a small permitted dataset.
5. Implement the frontend against catalog and routing fixtures, then integrate.

Each round updates its component brief, introduces actual lint/build/test
commands in CI, and documents remaining limitations without claiming completion
of components that still contain only a brief.
