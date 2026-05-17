# COMPETITORS — tt-trinity-phi (φ-anchor)

> Honest, evidence-backed positioning vs the commercial edge / data-centre NPU
> market. **TRI-NET does not compete on peak TOPS.** It competes on an open,
> high-assurance, ternary substrate with a reproducible spec-to-silicon path.
> This document collects what each competitor publicly claims, with source
> links, and then states what φ-anchor (this repo, the entry SKU) offers in
> response.

Vendor numbers below are paraphrased from public material at the linked
sources; we do not republish full specs. **Always check the vendor link
before quoting a number from this file** — vendor pages change.

---

## Reference axes

We measure every part on five axes:

1. **Open PDK / RTL** — can a third party fab a compatible part from
   published sources?
2. **Numeric basis** — what numeric formats does the part use natively?
3. **Provenance / proof trace** — can you prove which silicon you have and
   that it executed what it claims?
4. **Formal-assurance posture** — does the vendor publish formal proofs,
   bounded-rationality guarantees, or independent verification artefacts?
5. **Headline performance** — what does the vendor publish?

---

## Commercial parts (public material)

### Qualcomm Cloud AI 100 Ultra

- Source: [Qualcomm Cloud AI 100 Ultra product brief (PDF)](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Prod-Brief-QCOM-Cloud-AI-100-Ultra.pdf).
- Posture: data-centre inference card; multi-billion-parameter LLM serving.
- Open PDK / RTL: **No**.
- Numeric basis: FP / INT precisions documented in the brief (per vendor).
- Formal assurance: not published.

### Hailo-8

- Source: [Hailo-8 AI accelerator product page](https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/).
- Posture: edge AI accelerator (M.2 / on-board).
- Open PDK / RTL: **No**.
- Numeric basis: vendor-specified precisions, optimised for CNNs.
- Formal assurance: not published.

### Axelera Metis (AIPU)

- Source: [Axelera Metis AIPU product page](https://axelera.ai/ai-accelerators/aipu/metis).
- Posture: edge AI accelerator with in-memory-compute messaging.
- Open PDK / RTL: **No**.
- Numeric basis: vendor-specified (in-memory-compute integer paths).
- Formal assurance: not published.

### Google Coral Edge TPU

- Source: [Coral Edge TPU benchmarks](https://www.coral.ai/docs/edgetpu/benchmarks/).
- Posture: small-footprint edge TPU; mature toolchain.
- Open PDK / RTL: **No**.
- Numeric basis: int8 (quantised TFLite).
- Formal assurance: not published.

### MediaTek Dimensity NPUs (e.g. NPU 890 / Dimensity 9400+)

- Source: [MediaTek Dimensity 9400+ product page](https://www.mediatek.com/products/smartphones/mediatek-dimensity-9400-plus).
- Posture: integrated mobile-SoC NPU for on-device GenAI.
- Open PDK / RTL: **No** (integrated in proprietary SoC).
- Numeric basis: vendor-specified (FP / INT mix).
- Formal assurance: not published.

---

## Side-by-side, axes 1–4

The cells below describe **publicly documented posture**, not benchmarked
results. Cells marked "✅" require a documentation anchor; cells marked
"❌ (not public)" mean we found no public source — not that the property is
necessarily absent in the vendor's internal work.

| Axis → | Open PDK / RTL | Native ternary {−1,0,+1} | Reproducible spec-to-RTL | Formal-assurance artefacts |
|---|---|---|---|---|
| Qualcomm Cloud AI 100 Ultra | ❌ (closed) | ❌ (not public) | ❌ (closed) | ❌ (not public) |
| Hailo-8 | ❌ (closed) | ❌ (not public) | ❌ (closed) | ❌ (not public) |
| Axelera Metis | ❌ (closed) | ❌ (not public) | ❌ (closed) | ❌ (not public) |
| Google Coral Edge TPU | ❌ (closed) | ❌ (int8 only, public) | ❌ (closed) | ❌ (not public) |
| MediaTek Dimensity NPU | ❌ (closed) | ❌ (not public) | ❌ (closed) | ❌ (not public) |
| **TRI-NET line (this repo + siblings)** | ✅ SKY130A + Apache-2.0 | ✅ design intent + GF-family RTL ([`specs/numeric/`](specs/numeric/)) | ✅ `.t27 → RTL → shuttle` ([`info.yaml`](info.yaml), [`.github/workflows/gds.yaml`](.github/workflows/gds.yaml)) | ✅ Lucas POST proof seed + Coq trees ([`coq/`](coq/), [`trios-coq/`](trios-coq/)) — see [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md) |

A blank cell in the commercial column is a documentation gap, not an
accusation; if a vendor publishes such artefacts, we'll add the link in a
PR.

---

## Axis 5 — headline performance: where we are honest

TRI-NET on SKY130A (a 130 nm open educational PDK) **will not** match peak
TOPS of a 4 nm commercial part. Quoting vendor TOPS numbers here would be
misleading. Instead, see [`BENCHMARKS.md`](BENCHMARKS.md) for:

- What is actually measured today on this repo (canonical anchor, Lucas POST,
  cell counts).
- Which numbers are *architecture projections* (the 22FDX projection cited
  in the README Green-AI section) — clearly labelled as projections.

The README has a "Honest Performance Disclosure" section (R5-HONEST) that
states this in product terms; this document is its competitor-facing twin.

---

## Why TRI-NET, not a commercial NPU?

φ-anchor (this repo) is the entry SKU. You pick TRI-NET — and start with
φ-anchor — when at least one of these is true:

1. **You need open silicon end-to-end.** PDK, RTL, toolchain, shuttle path
   are all open under Apache-2.0. No vendor SDK lock-in.
2. **You care about proof / provenance.** Each die self-identifies via
   the Lucas POST and emits the canonical `0x47C0` cross-die anchor on
   reset; the same constant ties all three TRI-NET dies together.
3. **You are researching ternary or GoldenFloat numerics.** The `.t27`
   format registry covers GF4..GF256, FP8 E4M3 / E5M2, NF4, Posit16, int4,
   int8, binary16 (see [`specs/numeric/`](specs/numeric/)). Public
   commercial parts do not offer this format breadth at this level of
   openness.
4. **You want CLARA-aligned formal-assurance artefacts.** See
   [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md) for the evidence map
   and [`docs/CLARA_PROOF_MANIFEST.md`](docs/CLARA_PROOF_MANIFEST.md) for
   the proof manifest.
5. **You want a small, cheap entry chip.** 1×1 TT tile, $-class shuttle
   slot, single-tile pinout.

If your only need is "maximum on-device TOPS at minimum integration cost",
a commercial NPU is the right choice; we will not pretend otherwise.

---

## Source links (canonical references for this document)

- DARPA CLARA programme — <https://www.darpa.mil/research/programs/clara>
- Qualcomm Cloud AI 100 Ultra product brief (PDF) — <https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Prod-Brief-QCOM-Cloud-AI-100-Ultra.pdf>
- Hailo-8 product page — <https://hailo.ai/products/ai-accelerators/hailo-8-ai-accelerator/>
- Axelera Metis (AIPU) — <https://axelera.ai/ai-accelerators/aipu/metis>
- Google Coral Edge TPU benchmarks — <https://www.coral.ai/docs/edgetpu/benchmarks/>
- MediaTek Dimensity 9400+ — <https://www.mediatek.com/products/smartphones/mediatek-dimensity-9400-plus>
- BitNet b1.58 (ternary LLM motivation) — <https://arxiv.org/abs/2402.17764>
- Tiny Tapeout shuttle catalogue — <https://tinytapeout.com/chips/>

If a link 404s or the vendor changes their page, open an issue or PR —
this document is meant to stay up-to-date with public material.
