# [EN-02] `bench/22fdx/` projection notebook (reproducible band)

**Local plan ID:** `#6` (placeholder).
**Track:** EN-02.
**SIP section:** §3.
**Labels:** `track:EN`, `area:projection`, `r5:projection`, `type:bench`.

## Goal (target)

Author the projection notebook called for by
[`TOPS_W_22FDX_PROJECTION.md`](../../TOPS_W_22FDX_PROJECTION.md) §4,
so the existing **28–120 TOPS/W** band is reproducible from the
per-module estimates in [`BENCHMARKS.md`](../../BENCHMARKS.md) §"Cell-count snapshot".

## Scope

- `bench/22fdx/projection.ipynb` (or `.py`) regenerating the table in `TOPS_W_22FDX_PROJECTION.md` §2.
- Inputs: cell-count snapshot rows + assumption list (`TOPS_W_22FDX_PROJECTION.md` §3).
- Output: identical band; any drift is a bug.

## Done when

- [ ] Notebook commits + runs end-to-end with documented dependencies.
- [ ] CI smoke executes the notebook (optional — skip on Windows).
- [ ] `SPEC-22FDX-1` checkbox closed in [`STATUS.md`](../../STATUS.md).

## Anti-claims

- The output is `projection`, not measurement.
- No silicon TOPS/W claimed.
- "Peer-review pending" status remains — running the notebook does not satisfy peer review.
