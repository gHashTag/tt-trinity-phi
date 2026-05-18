# LINEUP — TRI-NET line

> Open, high-assurance, ternary AI silicon substrate built on the SKY130A
> open PDK and Tiny Tapeout shuttles. Three chips and one toolchain. This
> document is the canonical positioning index — every TRI-NET repo links
> back to it.

This repo (`tt-trinity-phi`) is the **φ-anchor**: the smallest, simplest
member of the line, and the reference identity / provenance chip the other
two dies anchor against.

---

## The line at a glance

| Repo | Role | Tile size | Posture | Position in the line |
|------|------|-----------|---------|----------------------|
| **tt-trinity-phi** *(this repo)* | **φ-anchor** — Lucas POST, canonical 0x47C0 anchor, proof seed, silicon provenance. | **1×1** | Reference / entry SKU. Must close cleanly. | Identity anchor — emits the same canonical 0x47C0 the other two dies cross-check against (TG-TRIAD-X). |
| [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) | **e-engine** — safety/control engine. | 8×2 | Safety-oriented control path. | Holds the SUPER-CROWN safety modules and the bulk of the t27 ISA. |
| [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) | **γ-surface** — 32-PE ternary mesh. | 8×4 | Throughput surface. | Carries the full PE mesh for ternary inference workloads. |
| `t27` (toolchain) | **Spec-to-RTL toolchain + numeric format registry**. | n/a | Hosted alongside the chips (see [`specs/numeric/`](specs/numeric/) for the registry imported into this repo). | Single source of truth for numeric formats (GF4..GF256, FP8 E4M3/E5M2, NF4, Posit16, int4/int8, binary16). The three chips all consume the same `.t27` specs. |

The same canonical anchor — `dot4(1.0, 2.0, 3.0, 4.0) = 0x47C0` in GF16(2⁴)
— is emitted by all three dies on power-up. That is the **cross-die ledger
anchor** (PhD Theorem 36.1). If two dies disagree on 0x47C0, the ledger
flags the discrepancy.

---

## Why φ-anchor is the entry SKU

φ-anchor is the chip you buy / fab / verify **first**, because:

1. **Smallest TT footprint** (1×1) — most likely to close DRC/LVS/STA cleanly.
2. **Simplest pinout** — single GF16 tile + canonical default datapath + POST
   status byte. No mesh, no D2D fabric on-die.
3. **Carries the proof seed** — the Lucas L₂..L₇ POST proving φ²+φ⁻²=3 lives
   here. POST status leaves the chip on `{uo_out[7:6], uo_out[5:0]}` when
   `load_mode=0`. This proof seed is what the larger dies inherit-by-reference.
4. **Silicon provenance** — die-unique HWRNG nonce (`hwrng_lfsr.v`), Lucas POST
   sticky-fail bit, and friend/foe handshake combine to make each φ-anchor
   die individually addressable on the TRI-NET fabric.
5. **Entry SKU economics** — single tile, single shuttle slot, low BoM. Used
   as the "hello world" of TRI-NET integration.

The other two repos do not duplicate the proof seed: they reference it.

---

## Positioning vs the commercial NPU market

TRI-NET is **not** a raw-TOPS competitor to Hailo-8, Qualcomm Cloud AI 100
Ultra, Axelera Metis, Google Coral Edge TPU, or MediaTek Dimensity NPUs.
We compete on a different axis:

| Axis | Commercial NPUs | TRI-NET |
|------|----------------|---------|
| Peak TOPS | High (commercial advantage) | Modest — SKY130A demonstrator node. |
| Open PDK | No | Yes — SKY130A, Apache-2.0 RTL. |
| Numeric basis | int8 / FP8 / FP16 | Ternary {−1, 0, +1} + GoldenFloat family (GF4..GF256). |
| Provenance / proof trace | Vendor attestation only | Reproducible `.t27 → RTL → shuttle` path; POST proves identity. |
| Formal assurance | Closed | CLARA-aligned, Coq trees in-repo (work in progress). |
| Use case | Throughput edge inference | High-assurance / research / formal-friendly inference and signal processing. |

See [`COMPETITORS.md`](COMPETITORS.md) for the evidence-linked breakdown of
each commercial part.

---

## Pick-the-right-chip guide

| If you want to… | Use |
|---|---|
| Validate the TRI-NET toolchain end-to-end with the cheapest, smallest die. | **tt-trinity-phi** (this repo). |
| Run a safety-bounded control loop with restraint / POST guarantees. | **tt-trinity-euler**. |
| Run a ternary inference workload on a 32-PE mesh. | **tt-trinity-gamma**. |
| Author or audit numeric formats consumed by all three chips. | **t27** (`specs/numeric/`). |

---

## Cross-repo navigation

- This repo: **φ-anchor**, see [`STATUS.md`](STATUS.md), [`README.md`](README.md), [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md), [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md), [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md), [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md), [`TRI_NET_API.md`](TRI_NET_API.md), [`WHITEPAPER.md`](WHITEPAPER.md), [`TOPS_W_22FDX_PROJECTION.md`](TOPS_W_22FDX_PROJECTION.md).
- [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) — e-engine.
- [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) — γ-surface.
- Tiny Tapeout shuttle index: <https://tinytapeout.com/chips/>.

---

## References

- DOI for the φ-anchor: [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877).
- DARPA CLARA programme: <https://www.darpa.mil/research/programs/clara>.
- BitNet b1.58 (ternary LLMs, motivates the ternary substrate): <https://arxiv.org/abs/2402.17764>.
- Tiny Tapeout chip catalogue: <https://tinytapeout.com/chips/>.
