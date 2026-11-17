# Repository implementation guidance

Read [the main architecture](../ARCHITECTURE.md) before making product changes.
Then read `components/<component>/ARCHITECTURE.md` for every component affected
by the task. These briefs are the handoff documents for successive rounds.

- Respect the owner's six component boundaries and the open-questions table.
  Ask for decisions that change scope or boundaries; choose ordinary technical
  details yourself and document them in the affected brief.
- Implement only the requested round. This repository starts as documentation
  and workflow scaffolding; do not assume working services or test commands.
- Keep comparison projects and home locations client-side only. Do not add
  accounts, project persistence on a server, or location-bearing telemetry.
- Pin the routing engine to the requested OTP v2.10 release line; verify its
  supported modes rather than silently replacing it or promising unsupported
  car/transit combinations.
- Use stable school IDs and explicit source, retrieval, year/edition, and schema
  metadata across data producers and consumers. Preserve unknown values.
- Honor source permissions and attribution. Test ingestion with small synthetic
  fixtures; CI must not scrape real websites or download regional datasets.
- Assume Ollama is available infrastructure-wide; do not add a model-hosting
  component. Validate any model-assisted extraction against schemas and source
  evidence, treat page content as untrusted, and mock model calls in CI.
  Never send private project data or home locations to the model endpoint.
- Validate external URLs, archives, scraped content, and imported JSON. Never
  commit credentials, personal project exports, downloaded datasets, or graphs.
- When introducing code, add focused tests, reproducible dependency locks,
  actual run/build/test instructions, and component-specific CI checks.
  Update both producer and consumer briefs when changing an interface.
- Keep scaffold checks distinct from application tests. Do not add no-op tests,
  Dockerfiles, or deployments that imply unimplemented features are working.
