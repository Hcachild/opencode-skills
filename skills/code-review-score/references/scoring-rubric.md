# Scoring rubric and smell baseline

## Severity

| Level | Meaning | Merge impact |
|---|---|---|
| High | Wrong behaviour, data corruption, security, silent fake of authoritative audit/state | Block merge |
| Medium | Misleading labels, incomplete honesty of diagnostics, historical mis-attribution, missing in-scope fields | Prefer fix before merge |
| Low | Naming, dual shapes, extra taxonomy, docs polish | Nits / follow-up OK |
| Out of scope | Required by parent PRD but not this PR's claimed slice | List separately; do not subtract heavily |

## Dimension guide

### Spec fit (in-scope) — 30%

- 90–100: All in-scope requirements covered; labels match matrix/spec; out-of-scope clearly carved out
- 75–89: Core covered; 1–2 medium gaps (wording, honesty of derived fields)
- 60–74: Partial; important in-scope fields missing or wrong semantics
- <60: Implements the wrong thing or invents behaviour the spec forbids

### Correctness — 25%

- 90–100: Edge cases handled; no forged defaults presented as recorded truth
- 75–89: Main path correct; a few edge/merge bugs
- 60–74: Subtle wrongness under “happy” incomplete data
- <60: Breaks main path or corrupts user-visible decisions

### Code quality / Standards — 20%

- Hard documented-standard violations cap this dimension at ≤60
- Smells alone usually land 70–85 if structure is still readable
- Deduct for shotgun edits, duplicated catalogs (FE/BE), unexplained dual representations

### Tests / verification — 15%

- 90–100: Targeted tests for merge/forge/edge cases + green CI or equivalent
- 75–89: Good unit coverage; API/CI skipped with explained env issue
- 60–74: Thin tests; happy path only
- <60: No meaningful verification

### Docs / maintainability — 10%

- Workstream / PR body that states decisions and rejected alternatives scores high
- Missing “why” or contradictory docs scores low

## Overall → merge mapping

| Overall | Default recommendation |
|---|---|
| ≥90 | Approve |
| 80–89 | Approve with nits |
| 70–79 | Request changes (or Merge now + follow-up only if urgency + low blast radius) |
| <70 | Request changes |

Override upward only when all High findings are absent and remaining Medium items are display-copy only.
Override downward if any High finding exists, even if the weighted score looks high.

## Smell baseline (Fowler, judgement only)

Repo-documented standards override these. Each finding is a labelled heuristic ("possible Feature Envy"), never a hard fail by itself.

- **Mysterious Name** — name does not reveal role → rename; if no honest name, design is murky
- **Duplicated Code** — same shape in multiple hunks → extract shared helper
- **Feature Envy** — method uses another object's data more than its own → move onto that data
- **Data Clumps** — same fields travel together → bundle a type
- **Primitive Obsession** — string/number standing for a domain concept → small type
- **Repeated Switches** — same cascade on one type → polymorphism or shared map
- **Shotgun Surgery** — one change touches many files → gather into one module
- **Divergent Change** — one module edited for unrelated reasons → split
- **Speculative Generality** — abstraction unused by the spec → delete/inline
- **Message Chains** — long `a.b().c().d()` → hide behind one method
- **Middle Man** — mostly delegates → call target directly
- **Refused Bequest** — ignores most inherited API → prefer composition

## Scope carve-out rules

When the parent PRD is large (e.g. QA online + Langfuse + tools) but the PR only claims diagnostics/UI/API display:

- Credit Spec fit for surfacing audit fields, matrix labels, non-fabrication
- Do **not** fail for missing runtime provider, Langfuse tree, or public reply templates unless the PR claims them
- Do fail if diagnostics **misrepresent** authoritative audit (forged defaults, wrong matrix labels, cross-run merge)
