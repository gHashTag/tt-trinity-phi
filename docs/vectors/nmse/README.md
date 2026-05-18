# NMSE Golden Vectors — GF16 vs bfloat16

> **Readiness:** **SPEC / GOLDEN REFERENCE.** The JSON files in this
> directory are reference *baselines* for the NMSE protocol pinned by
> [`../../../GF16_BFLOAT16_NMSE.md`](../../../GF16_BFLOAT16_NMSE.md).
> They are **not** silicon captures; they are not even computed by a
> harness in this repo yet. They exist so a future harness has a
> contract to match.

Last updated: 2026-05-18.

---

## What is in this directory

| File | Purpose |
|---|---|
| [`gf16_vs_bfloat16.golden.json`](gf16_vs_bfloat16.golden.json) | The canonical golden-reference vector: seed, distribution catalogue, baseline NMSE values, tolerances, and provenance fields. All NMSE-related claims in the repo cross-reference this file. |

The schema is intentionally a strict superset of the per-run report
format described in
[`GF16_BFLOAT16_NMSE.md`](../../../GF16_BFLOAT16_NMSE.md) §5 — a future
harness can emit one of these for every run and diff against the
golden vector with the documented tolerances.

---

## What these vectors are NOT

- **Not measured silicon.** `provenance.mode` is fixed to `RTL_ONLY`.
  Any vector with `provenance.mode = "SILICON"` would be a different,
  silicon-anchored artefact that this repo does not (yet) produce.
- **Not a published benchmark.** No file under
  [`bench/nmse/`](../../../) is yet committed; once a harness exists,
  per-commit reports land there, not here.
- **Not a tolerance for the algorithm.** The `tolerance_db` field
  bounds *implementation drift* between a host harness and the
  reference protocol, not the algorithm's information-theoretic floor.

---

## Verification

The spec gate
[`../../../scripts/check_trinet_specs.sh`](../../../scripts/check_trinet_specs.sh)
loads `gf16_vs_bfloat16.golden.json` and verifies:

1. The schema fields required by the matrix's `VC-NMSE-*` rows exist.
2. `sample_count == 1048576`.
3. `seed == "0x47C0"`.
4. Distributions `D-1..D-6` are all present.
5. `provenance.mode != "SILICON"` (R5 honesty).
6. For every distribution, both `gf16` and `bfloat16` baselines exist
   with finite `nmse_db` and a positive `tolerance_db`.

If any of these checks fail, the gate reports a spec bug.

---

## How a future harness should use this

1. Generate `N = 1,048,576` samples per distribution with seed
   `0x47C0`, using the per-distribution generator notes in
   [`GF16_BFLOAT16_NMSE.md`](../../../GF16_BFLOAT16_NMSE.md) §3.
2. Compute f32 ground truth, quantise/dequantise via GF16 and bf16,
   compute NMSE in dB per the §2 formula.
3. Compare against `expected.nmse_db` in this file, allowing
   `±tolerance_db`.
4. Emit a per-run report under `bench/nmse/<git_sha>.json` with the
   same schema *plus* an `actual` block.

The vectors here are the **target** — they live in `docs/` because
they are spec, not output.
