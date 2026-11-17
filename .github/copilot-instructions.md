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

## Coding behavior (Karpathy guidelines)

Adapted from [karpathy-guidelines](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md)
(MIT license), based on Andrej Karpathy's observations on LLM coding pitfalls.
They favor caution over speed; use judgment for trivial tasks.

1. **Think before coding.** State assumptions explicitly. If several
   interpretations exist, present them rather than choosing silently. Mention
   simpler approaches and push back when warranted. If something is unclear,
   stop, name it, and ask.
2. **Simplicity first.** Write the minimum code that solves the problem: no
   unrequested features, single-use abstractions, speculative configurability,
   or error handling for impossible scenarios. If 200 lines could be 50, rewrite.
3. **Surgical changes.** Touch only what the request requires. Do not improve
   adjacent code, comments, or formatting; match existing style. Remove only
   imports/variables/functions your change orphaned; mention, don't delete,
   unrelated dead code. Every changed line should trace to the request.
4. **Goal-driven execution.** Turn tasks into verifiable goals (reproduce a bug
   with a test, then fix it; keep tests passing across a refactor). For
   multi-step work, state a brief plan with a verification for each step.

## Open questions

Owner decisions are tracked in the open-questions table in `ARCHITECTURE.md`;
see `.github/instructions/open-questions.instructions.md` for how to handle them.
