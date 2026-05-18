# WHITEPAPER — TRI-NET value proposition & links (φ-anchor view)

> **Readiness:** **SPEC / pointer-only**. This file is the φ-anchor-side
> hub for the TRI-NET whitepaper material — it does **not** restate
> performance claims. Numeric and silicon claims are gated by
> [`STATUS.md`](STATUS.md) and [`BENCHMARKS.md`](BENCHMARKS.md); the
> whitepaper is the **narrative** layer on top of those, not a license
> to skip the readiness ladder.

Last updated: 2026-05-18.

---

## 1. One-paragraph value proposition

TRI-NET is an open-PDK, ternary-arithmetic AI silicon substrate
optimised for **assurance** and **reproducibility** rather than peak
TOPS. φ-anchor (this repo) is the smallest die of the line: a 1×1
SKY130A Tiny Tapeout chip whose job is to **emit a single canonical
constant** (`0x47C0 = dot4(1,2,3,4)` in GF16) and **prove the φ-anchor
identity** `φ² + φ⁻² = 3` through the Lucas L₂..L₇ POST. The bigger
dies in the line (e-engine, γ-surface) anchor against it. Apache-2.0
RTL, t27-driven format registry, CLARA-aligned proof trace.

---

## 2. Who this is for

| Audience | What TRI-NET offers | Where to start |
|----------|---------------------|----------------|
| **Open-hardware researchers** | Apache-2.0 RTL on an open PDK (SKY130A) with a reproducible `.t27 → RTL → shuttle` pipeline. | [`README.md`](README.md), [`docs/INDEX.md`](docs/INDEX.md). |
| **AI-safety / assurance teams** | CLARA-aligned proof trace ([`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md)); restraint controller is a protocol-level kill switch ([`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) §2). | [`docs/TRI_NET_DARPA_CLARA_PROPOSAL.md`](docs/TRI_NET_DARPA_CLARA_PROPOSAL.md). |
| **Numeric-format researchers** | The GoldenFloat family (GF4..GF256) and the NMSE comparison protocol against bfloat16. | [`specs/numeric/formats.t27`](specs/numeric/formats.t27), [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md). |
| **Integrators / bridge authors** | A frozen wire-level protocol (TIP v1.0) and a small, stable pin interface. | [`TRI_NET_API.md`](TRI_NET_API.md), [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md). |
| **Competitive analysts** | Honest framing against commercial NPUs (we are not a TOPS competitor). | [`COMPETITORS.md`](COMPETITORS.md), [`LINEUP.md`](LINEUP.md). |

---

## 3. The five differentiators (anchored)

Each row links back to the **evidence** in this repo, not to marketing
prose. Anything that lacks a link is a future claim, not a current one.

| # | Differentiator | Where it is anchored |
|---|----------------|----------------------|
| 1 | Open PDK + Apache-2.0 RTL                                        | [`LICENSE`](LICENSE), [`info.yaml`](info.yaml), [`.github/workflows/gds.yaml`](.github/workflows/gds.yaml) |
| 2 | Reproducible spec → RTL pipeline (`.t27` driven)                 | [`specs/numeric/`](specs/numeric/), [`specs/fpga/`](specs/fpga/), [`rtl_gen/`](rtl_gen/) |
| 3 | Cross-die canonical anchor (`0x47C0`, TG-TRIAD-X)                | [`src/gf16_dot4.v`](src/gf16_dot4.v), [`.github/workflows/tri-test.yml`](.github/workflows/tri-test.yml) |
| 4 | Lucas L₂..L₇ POST proving `φ² + φ⁻² = 3` (provenance seed)       | [`src/phi_anchor_post.v`](src/phi_anchor_post.v), [`src/lucas_rom.v`](src/lucas_rom.v) |
| 5 | CLARA-aligned proof trace (Gap-4 restraint, Coq references)      | [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md), [`docs/CLARA_PROOF_MANIFEST.md`](docs/CLARA_PROOF_MANIFEST.md), [`coq/`](coq/), [`trios-coq/`](trios-coq/) |

The **R-SI-1** constraint (zero `*` operators) is a constraint, not a
differentiator on its own — it is what makes (1), (2), and (3) cheap.
See [`docs/R-SI-1.md`](docs/R-SI-1.md).

---

## 4. Whitepaper artefacts

The full whitepaper lives outside this repo; this section is the
landing page for it.

| Artefact | Where | Status |
|----------|-------|--------|
| **PhD chapter (Ch. 36 TRI-1 Triad)**                       | [`flos_70.tex` in `gHashTag/trios`](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex) | Published in upstream repo. |
| **DARPA CLARA proposal**                                   | [`docs/TRI_NET_DARPA_CLARA_PROPOSAL.md`](docs/TRI_NET_DARPA_CLARA_PROPOSAL.md) | In-repo, draft. |
| **Zenodo DOI bundle**                                      | [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877) | Anchored at TTSKY26b shuttle commit. |
| **Numeric formats summary**                                | [`docs/TRI_NET_FORMATS_SUMMARY.md`](docs/TRI_NET_FORMATS_SUMMARY.md) | In-repo. |
| **TRI-NET line positioning**                               | [`LINEUP.md`](LINEUP.md) | In-repo. |
| **Whitepaper PDF (consolidated)**                          | *Planned* — to be uploaded to the Zenodo record. | Not yet uploaded; see [`README.md`](README.md#zenodo--22fdx-projection-bundle-readiness) once that row is added. |

The PDF row is the **only** planned artefact; everything else is
already present and linked.

---

## 5. What this document is NOT

- **Not** a substitute for [`BENCHMARKS.md`](BENCHMARKS.md). Any
  numeric claim made in narrative form here must back-link to a row in
  the BENCHMARKS measured / projected tables.
- **Not** a feature wishlist. Items in [`STATUS.md`](STATUS.md)
  "immediate checklist" are the only forward-looking commitments.
- **Not** a competitive-tear-down. See [`COMPETITORS.md`](COMPETITORS.md)
  for the honest peak-TOPS framing.

---

## 6. Cross-references

- [`README.md`](README.md) — top-level entry point.
- [`STATUS.md`](STATUS.md) — readiness ladder.
- [`LINEUP.md`](LINEUP.md) — TRI-NET line positioning.
- [`BENCHMARKS.md`](BENCHMARKS.md) — measured / projected breakdown.
- [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md) — assurance evidence map.
- [`COMPETITORS.md`](COMPETITORS.md) — peak-TOPS framing.
- [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) — chip-to-chip role layer.
- [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) — NMSE protocol.
- [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) — power-deck status.
- [`TRI_NET_API.md`](TRI_NET_API.md) — external-integration index.
- [`docs/SCIENTIFIC_IMPROVEMENT_PLAN.md`](docs/SCIENTIFIC_IMPROVEMENT_PLAN.md) — 2026 scientific improvement plan (φ-anchor view), `target` / `projection` / `VERIFY` labelled.
