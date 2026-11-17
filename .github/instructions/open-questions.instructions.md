---
applyTo: "**/ARCHITECTURE.md"
---

# Discussing and resolving open questions

The "Open questions for the owner" table in the root `ARCHITECTURE.md` records
decisions that belong to the repository owner (scope, component boundaries,
data sources and licensing, privacy, hosting). Technical details are yours.

- Before implementing, check whether the work depends on an open question. If
  it does, ask the owner rather than choosing an answer.
- When asking, state the question, 2-3 realistic options with trade-offs, and
  your recommendation. Ask one decision at a time; do not bundle unrelated ones.
- Record the owner's answer in the table (replace `Open`, keep the question
  text) and update every affected component brief, producer and consumer alike.
- Add newly discovered owner-level questions to the table; do not resolve them
  silently or bury them in a component brief.
- Do not mark a question answered based on assumptions, sample data, or your
  own recommendation. Do not expand scope or change component boundaries
  without an explicit owner decision.
