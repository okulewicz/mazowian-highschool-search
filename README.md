# mazowian-highschool-search
A bunch of components making a POC for selecting perfect high school

## Implementation status

The `transport-data` refresh container and OTP v2.10 graph build/serve process
are implemented. Other component briefs remain placeholders; there is no
school-data ingestion or frontend yet.

- [Architecture and owner decisions](ARCHITECTURE.md)
- [Copilot implementation guidance](.github/copilot-instructions.md)

## Components

Each directory represents a component or designated process. Its
`ARCHITECTURE.md` documents the current artifact contract and remaining work.

| Component | Implementation brief |
| --- | --- |
| Mazovian GTFS and OSM downloader | [Transport data](components/transport-data/ARCHITECTURE.md) |
| OpenTripPlanner v2.10 engine | [Routing](components/routing/ARCHITECTURE.md) |
| High school website and location extractor | [School discovery](components/school-discovery/ARCHITECTURE.md) |
| School profiles, admission points, fees, open days, and deadlines parser | [School details](components/school-details/ARCHITECTURE.md) |
| Perspektywy ranking importer | [School rankings](components/school-rankings/ARCHITECTURE.md) |
| Browser-local comparison projects and map | [Frontend](components/frontend/ARCHITECTURE.md) |

## Automation

[CI](.github/workflows/ci.yml) checks required scaffold files and committed
whitespace on pull requests and pushes. Transport-data fixture tests run
offline; CI does not download regional feeds or build a regional OTP graph.

[Copilot setup](.github/workflows/copilot-setup-steps.yml) checks out the
repository without installing speculative application dependencies.

## Local transport and routing pipeline

Requires Docker Compose v2 and Python 3.12+ on the host. Data and graphs live in
ignored `./.data/`; do not commit them. The configured static GTFS feeds are
from the Kuran index and OSM is the Geofabrik Mazowieckie extract. Review the
upstream terms linked in
[`components/transport-data/sources.json`](components/transport-data/sources.json)
before use or redistribution. Realtime feeds are intentionally not downloaded
or merged into static schedules.

```sh
docker compose --profile jobs build transport-data
docker compose --profile jobs run --rm transport-data
python3 components/routing/build_graph.py .data
docker compose up otp
```

The refresh creates an immutable snapshot under `.data/transport/snapshots/`
and atomically updates `.data/transport/current`. The graph command verifies
the snapshot manifest and checksums, runs graph construction in the pinned OTP
container, performs a GraphQL API smoke query, and only then updates
`.data/routing/active`. Failed refreshes/builds leave the previous pointer
unchanged. Refresh and graph build are explicit, separate commands; refreshing
does not replace the graph currently being served. To use a newly refreshed
snapshot, build and smoke-test its graph, then restart OTP:

```sh
docker compose restart otp
```

OTP is available at `http://localhost:8080`; its GTFS GraphQL endpoint is
`http://localhost:8080/otp/gtfs/v1`. The smoke test checks that endpoint, not
every routing mode or the production frontend query. Car/transit combinations
and realtime behavior have not been verified by this fixture. OTP receives
request coordinates; keep routing requests out of logs. Coverage approval,
refresh cadence, public hosting, and scheduling remain owner decisions.

Focused offline checks:

```sh
python3 -m unittest discover -s components/transport-data -p 'test_*.py'
python3 -m unittest discover -s components/routing -p 'test_*.py'
```
