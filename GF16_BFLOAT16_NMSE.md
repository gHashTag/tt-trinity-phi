# GF16 vs bfloat16 — NMSE Standard Comparison Protocol (φ-anchor view)

> **Readiness:** **SPEC (draft)**. This document specifies the standard
> protocol for comparing the GoldenFloat-16 (GF16) numeric format against
> IEEE bfloat16 by **normalised mean-squared error (NMSE)**, and pins
> down how φ-anchor participates in (and anchors the provenance of) that
> measurement. No measured NMSE numbers are claimed here yet — the
> harness this document specifies has not yet been added to the repo.

Last updated: 2026-05-18.

---

## 1. Why this protocol exists

GF16 and bfloat16 both occupy 16 bits but differ on layout (see
[`specs/numeric/formats.t27`](specs/numeric/formats.t27) §1):

| Format    | Sign | Exp | Mantissa | Bias |
|-----------|------|-----|----------|------|
| GF16      | 1    | 6   | 9        | 31   |
| bfloat16  | 1    | 8   | 7        | 127  |

Any claim of the form "GF16 is comparable / better / worse than bfloat16
on workload X" must be backed by a **reproducible NMSE measurement** on
a fixed reference distribution, with the round-trip error reported
against a common f32 ground truth. This file defines that procedure so
two independent runs (one on a host, one anchored to a φ-anchor die) can
be compared like-for-like.

The protocol is **t27-linked**: the same numeric specs that drive RTL
generation (`specs/numeric/*.t27`) also drive the harness inputs, so
"the chip's idea of GF16" and "the harness's idea of GF16" cannot drift.
See [`docs/TRI_NET_FORMATS_SUMMARY.md`](docs/TRI_NET_FORMATS_SUMMARY.md)
for the format registry layout.

---

## 2. NMSE — definition used in this protocol

For a reference vector `x ∈ ℝ^N` and a quantised-then-decoded vector
`x̂`, NMSE is reported in dB:

```
NMSE_dB(x, x̂) = 10 * log10( Σ (xᵢ - x̂ᵢ)² / Σ xᵢ² )
```

Lower (more negative) is better. The protocol fixes:

- The reference distribution **D** (see §3).
- The **f32 ground-truth** computation `x` (always done in IEEE binary32).
- The **quantise / dequantise** path under test (GF16 or bfloat16).
- The **aggregation** (single NMSE over all N samples; no per-bin tricks).

---

## 3. Reference distributions (fixed)

The harness MUST report NMSE on **all** of the following distributions,
each with `N = 1,048,576` samples drawn from a fixed seeded RNG (seed
`0x47C0`, deliberately the canonical anchor):

| ID  | Distribution                                  | Rationale |
|-----|-----------------------------------------------|-----------|
| D-1 | Standard normal `N(0, 1)`                     | Generic activations. |
| D-2 | Lognormal `exp(N(0, 1))`                      | Weights with heavy tail. |
| D-3 | Uniform on `[-1, 1]`                          | Normalised activations. |
| D-4 | Mixture: 95% `N(0, 1)` + 5% `N(0, 16)`        | Outlier-heavy attention scores. |
| D-5 | Powers of two from `2^-30 .. 2^30`, uniform   | Dynamic-range stress test. |
| D-6 | The 75 sacred constants from `sacred_constants_rom.v` | φ-anchor-native canonical set; ties the test to the on-die ROM. |

D-6 is the **φ-anchor anchor** for the harness: a run that does not
match the on-die ROM round-trip is rejected before any other
distribution is scored.

---

## 4. φ-anchor's role in the measurement

φ-anchor does **not** itself execute the NMSE workload. The harness runs
on a host. φ-anchor anchors the measurement in two ways:

1. **Provenance anchor.** Each NMSE run records the canonical `0x47C0`
   reported by the φ-anchor die under test (or `RTL_ONLY` if no silicon
   is in the loop). A run whose 0x47C0 fails verification is invalid.
   See [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) §2 for the anchor's role.
2. **ROM round-trip anchor.** D-6 (the sacred-constants distribution)
   is read back from the φ-anchor's `sacred_constants_rom`
   ([`src/sacred_constants_rom.v`](src/sacred_constants_rom.v)) when
   the die is present. NMSE(D-6) is computed against the host's
   independently decoded reference; a delta >0 indicates a ROM /
   format-spec drift bug.

In the absence of silicon (current rung), the harness can run in
`RTL_ONLY` mode against iverilog. The provenance line in the report
MUST say `RTL_ONLY` so it is never confused with a measured-silicon
NMSE number.

---

## 5. Output format (one JSON object per run)

```json
{
  "protocol":         "GF16_BFLOAT16_NMSE/1.0",
  "git_sha":          "<short SHA of this repo>",
  "t27_format_sha":   "<sha256 of specs/numeric/gf16.t27>",
  "phi_anchor":       { "mode": "RTL_ONLY|SILICON", "anchor_word": "0x47C0", "verified": true },
  "sample_count":     1048576,
  "seed":             "0x47C0",
  "results": [
    { "dist": "D-1", "format": "gf16",     "nmse_db": -54.21 },
    { "dist": "D-1", "format": "bfloat16", "nmse_db": -47.83 },
    { "dist": "D-2", "format": "gf16",     "nmse_db": -38.12 },
    { "dist": "D-2", "format": "bfloat16", "nmse_db": -41.07 },
    "..."
  ]
}
```

(Numbers above are **illustrative**, not measured.)

Reports MUST be checked into the repo under `bench/nmse/<git_sha>.json`
once the harness exists. Until then, no `nmse_db` number is to appear
anywhere else in the repo, including the README's Green-AI section.

---

## 6. Acceptance criteria for "GF16 vs bfloat16" claims

Any document in this repo that states a directional GF16-vs-bfloat16
claim (e.g. "GF16 beats bfloat16 on heavy-tail activations") MUST:

1. Cite a JSON report under `bench/nmse/`.
2. Quote the report's `git_sha` and `t27_format_sha`.
3. Quote the distribution IDs (D-1..D-6) it relies on.
4. State whether the underlying provenance was `RTL_ONLY` or `SILICON`.

If a claim cannot do all four, it belongs in **PROJECTED** in
[`BENCHMARKS.md`](BENCHMARKS.md), not in narrative prose.

---

## 7. Implementation status (today)

| Item | Rung | Notes |
|------|------|-------|
| GF16 numeric spec                  | SPEC (in repo)      | [`specs/numeric/gf16.t27`](specs/numeric/gf16.t27), [`specs/numeric/formats.t27`](specs/numeric/formats.t27) |
| bfloat16 reference path            | Not in repo         | Host harness only; planned. |
| Harness `bench/nmse/`              | Not in repo         | Planned next-lineup. |
| φ-anchor anchor-word capture       | Available           | Via `tt-gds-action` artefact or iverilog `test/tb.v` log. |
| Sacred-ROM D-6 round-trip          | Available in sim    | Exercised partially by `test/tb.v`; needs a dedicated job. |

The README's Green-AI / numeric sections currently make **no NMSE
claim**. That posture is intentional and must be preserved until a
report lives in `bench/nmse/`.

---

## 8. Cross-references

- [`specs/numeric/gf16.t27`](specs/numeric/gf16.t27) — GF16 t27 spec.
- [`specs/numeric/formats.t27`](specs/numeric/formats.t27) — Format registry (incl. bf16).
- [`docs/TRI_NET_FORMATS_SUMMARY.md`](docs/TRI_NET_FORMATS_SUMMARY.md) — format catalogue.
- [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) — anchor / provenance role.
- [`BENCHMARKS.md`](BENCHMARKS.md) — where the report lands once it exists.
- [`STATUS.md`](STATUS.md) — readiness ladder.
