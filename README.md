# mazowian-highschool-search
A bunch of components making a POC for selecting perfect high school

## Scaffold status

This repository currently contains architecture and implementation briefs, not
working services. No downloads, scraping, routing, or frontend are implemented.

- [Architecture and owner decisions](ARCHITECTURE.md)
- [Copilot implementation guidance](.github/copilot-instructions.md)

## Components

Each directory represents a future Dockerized service or designated process.
Its `ARCHITECTURE.md` is the brief for a subsequent implementation round.

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
whitespace on pull requests and pushes. It does not yet run application tests
or build images. Add component-specific checks when their code is introduced.

[Copilot setup](.github/workflows/copilot-setup-steps.yml) checks out the
repository without installing speculative application dependencies. There are
currently no application lint, build, test, or run commands.
