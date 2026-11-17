# School profiles, admissions, fees, open days, and deadlines process

Status: placeholder; no website parsers or details artifacts exist yet.
Read [the main architecture](../../ARCHITECTURE.md) first.

## Responsibility and boundary

Extract class profiles, historical admission exam-point thresholds, and
private-school tuition/other stated fees, and discover open-door events and
important deadlines from school websites and approved linked admissions
sources. This is a containerized batch process consuming `school-discovery`
records. It must not create a separate school identity scheme or scrape rankings.

## Inputs and outputs

- Inputs: base catalog IDs/approved official websites and target school years.
- Output: versioned school details keyed by `school_id`, with per-field source
  URLs, retrieval times, source year, and extraction/review status.
- Profiles: source profile identifier/name, subjects, school year.
- Thresholds: profile, admission year/round, threshold value, and point scale
  where known. Distinguish past cutoffs from eligibility rules.
- Fees: amount, currency, billing period, fee type (tuition/enrollment/other),
  applicable year, and qualifiers. Missing fees do not mean free tuition.
- Non-point requirements: raw text, source links, and structured criteria where
  supported (for example portfolio or language certificate). Never coerce these
  into exam points.
- Open days: source text, exact date/time when stated, date precision, and event
  venue, which may differ from the school address. Keep missing years unknown.
- Important deadlines: applications, exams/interviews, portfolio submission,
  document delivery, and enrollment confirmation where applicable. Include
  event type, school and optional profile, admission cycle, start/end or due
  date, timezone for timed events, precision, source URL, and retrieval time.
- Preserve approximate dates and unparsed notices. Track changed/cancelled
  events when stated; distinguish past cycles from upcoming ones. Conflicting
  sources require visible uncertainty, not silent selection of a guessed date.

## Implementation round

1. Agree on years, point interpretation, and fee comparison rules with owner.
2. Define the details contract, then implement a small documented set of
   source adapters; mark unsupported layouts explicitly rather than guessing.
3. Add bounded/cached fetching and safe content parsing, honoring terms and
   robots policies; retain field provenance and uncertainty.
   Ollama is available for irregular page extraction. Use bounded requests,
   versioned prompts/model identifiers, validated structured output, and source
   evidence for each extracted fact. Missing evidence remains unknown; source
   content cannot instruct the model to invoke tools or change the task.
4. Discover relevant open-day and admissions-calendar pages on approved sites;
   extract events/deadlines with their admission cycle and update status.
   Do not assume the landing page contains all relevant dates.
5. Provide extraction/validation commands, container packaging, and atomic
   publication without losing prior good details on source failures.

## Acceptance checks

Use synthetic HTML fixtures for multiple profiles/years, Polish number formats,
monthly versus annual fees, missing/ambiguous thresholds, changed layouts, and
malicious content. Verify joins to stable discovery IDs and that unknown data
never becomes zero or an unsupported admission guarantee.
Cover non-point requirements, approximate open-day dates, alternate event
venues, and fees whose currency or billing period is unspecified.
Test deadlines from linked pages, date ranges, missing years/times, Polish date
formats, Europe/Warsaw timezone handling, profile-specific deadlines, cancelled
or rescheduled open days, conflicting notices, and historical admission cycles.
Mock Ollama responses in tests, including malformed output, unsupported claims,
prompt-injection text in pages, unavailable models, and timeouts. Never require
a live model for routine CI or publish inferred dates as sourced facts.
