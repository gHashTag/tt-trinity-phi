# [SN-01] Ternary round-trip row in NMSE harness

**Local plan ID:** `#8` (placeholder).
**Track:** SN-01.
**SIP section:** §4.
**Labels:** `track:SN`, `area:numeric`, `r5:target`, `type:bench`.

## Goal (target)

Add a `ternary` round-trip row to the NMSE harness contracted by
[`GF16_BFLOAT16_NMSE.md`](../../GF16_BFLOAT16_NMSE.md) §3 (D-1..D-6),
so the ternary substrate shared with SNN datapaths is covered.

## Scope

- Extend the harness format to support `ternary` next to `gf16` and `bfloat16`.
- Add a `ternary` row per distribution in the first report.
- Cite [`specs/numeric/formats.t27`](../../specs/numeric/formats.t27) `ternary` enum.

## Done when

- [ ] Harness lands (depends on PUB-02 issue).
- [ ] First report `bench/nmse/<sha>.json` includes ternary rows.

## Anti-claims

- No measured-silicon NMSE.
- No claim that ternary "beats" bf16 — the table is the claim.
