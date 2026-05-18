# [OS-03] `.github/PULL_REQUEST_TEMPLATE.md` with R5 checklist

**Local plan ID:** `#16` (placeholder).
**Track:** OS-03.
**SIP section:** §6.
**Labels:** `track:OS`, `area:governance`, `r5:target`, `type:template`.

## Goal (target)

Add a PR template whose checklist enforces R5 framing: no measured
silicon claim without a [`BENCHMARKS.md`](../../BENCHMARKS.md) MEASURED
row; no funding / acceptance claims; ultra-headline numbers labelled
`VERIFY`.

## Scope

- `.github/PULL_REQUEST_TEMPLATE.md` with a "Test plan" section and
  the R5 checklist.
- Reference [`docs/SCIENTIFIC_IMPROVEMENT_PLAN.md`](../../docs/SCIENTIFIC_IMPROVEMENT_PLAN.md) anti-claims as the rule of thumb.

## Done when

- [ ] Template lands and GitHub prefills it on new PRs.
- [ ] At least one subsequent PR uses the template fully.

## Anti-claims

- Templates suggest, they do not enforce — CI is the enforcer.
- This issue does **not** add a CI gate (that's EN-03).
