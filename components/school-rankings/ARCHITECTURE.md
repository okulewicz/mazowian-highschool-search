# Perspektywy school ranking import process

Status: placeholder; no ranking scraper, importer, or dataset exists yet.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Obtain permitted Perspektywy high school ranking data and reconcile it to
`school-discovery` identities. This is a containerized import process, separate
from school website parsing. It does not calculate a replacement ranking.

## Inputs and outputs

- Inputs: owner-approved editions/categories and a permitted source or export.
- Output: versioned ranking records keyed by `school_id`, with edition/year,
  geographic scope, school category, rank, published score if available,
  source URL, retrieval time, and attribution.
- Preserve edition/category distinctions and ties. Absence from a ranking
  means unranked/unknown, never rank zero.
- Maintain a reviewable mapping for ambiguous source-school matches; names
  alone must not automatically merge different schools.

## Implementation round

1. Confirm permission, attribution/redistribution terms, editions, and scope.
   If automated access is not permitted, ask the owner to approve a manual
   import path; do not bypass restrictions or silently change the source.
2. Define ranking schema and deterministic matching against discovery IDs.
3. Implement the permitted adapter with pacing/caching if networked; report
   unmatched entries and structural source changes instead of guessing.
4. Provide import/validation commands, container packaging, and safe snapshot
   publication retaining the prior good edition on failure.

## Acceptance checks

Use synthetic fixtures, not copied ranking tables: ties, multiple editions and
categories, homonymous schools, missing scores, ambiguous/unmatched records,
and changed source formats. Frontend consumption must retain schools with no
ranking and clearly label the edition being compared.
