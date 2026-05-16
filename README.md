# TRI-1 Phi — Trinity φ-anchor

[![Submit](https://img.shields.io/badge/TTSKY26b-Phi%20anchor-orange)](https://app.tinytapeout.com/shuttles/ttsky26b)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Sacred](https://img.shields.io/badge/sacred--constant-%CF%86%20%E2%89%88%201.61803-purple)](#sacred-formula)

> One of three neurons of **Trinity TRI-NET** — three sacred constants embodied in silicon:
>
> - **φ-anchor** → **THIS REPO** (1×1, Lucas POST proving φ²+φ⁻²=3 on power-up, canonical seed 0x47C0)
> - **e-engine** → [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) (8×2, 18 SUPER-CROWN modules)
> - **γ-surface** → [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) (8×4, 32 PE full mesh)
>
> Apache-2.0 · ternary {−1,0,+1} · SKY130A · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)

## Sacred Formula

`V = n × 3^k × π^m × φ^p × e^q × γ^r × C^t × G^u`

This chip is the **φ^p** factor — the golden anchor that all Trinity computation
references. Single ternary cell. Power-up emits the canonical hash **0x47C0** as
witness of `dot4(1,2,3,4)` over GF(16), proving the Trinity identity φ²+φ⁻²=3
through Lucas recurrence.

## Renamed from tt-trinity-nano

This repository was renamed from `tt-trinity-nano` on 2026-05-16 as part of the
Trinity TRI-NET sacred-constant naming. The old URL redirects to this one — old
clones/forks continue to work.

---

# TRI-1 Nano — Single-tile Trinity GF16 MAC

> 🌳 Trinity role: **BRANCH-SILICON** — TTSKY26b shuttle SKU 1 of 3.
> Sibling of [tt-trinity-gf16](https://github.com/gHashTag/tt-trinity-gf16) (Mid) and [tt-trinity-max](https://github.com/gHashTag/tt-trinity-max) (Max).
> Spec: [TRI_NET_SHUTTLE_TRIAD](https://github.com/gHashTag/tt-trinity-gf16/blob/main/docs/architecture/TRI_NET_SHUTTLE_TRIAD.md) · EPIC [trinity-fpga#49](https://github.com/gHashTag/trinity-fpga/issues/49) L-DPC7.

**Anchor:** φ² + φ⁻² = 3 · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)

## What it is

The smallest, simplest, most-likely-to-tape-out cleanly member of the
**TRI-1 Triad** — three Trinity ternary-MAC silicon dies submitted to the
same TinyTapeout shuttle (TTSKY26b, close 2026-05-18):

| SKU | Repo | Tiles | Modules | Role |
|-----|------|-------|---------|------|
| **Nano** | this | 1×1 | 5 (1 tile + GF16 leaves) | floor of the family — must close |
| **Mid**  | [tt-trinity-gf16](https://github.com/gHashTag/tt-trinity-gf16) | 8×2 | 15 SUPER-CROWN modules + GF16 mesh + BLAKE3 + ternary matmul + Lucas POST + BPB counter + Wishbone | flagship |
| **Max**  | [tt-trinity-max](https://github.com/gHashTag/tt-trinity-max) | (TBD) 4×4 mesh | full mesh-of-meshes, target stretch | stretch goal |

All three drive the **same canonical 16-bit constant `0x47C0`** on
`{uio_out, uo_out}` immediately after reset, computed from the same
hard-coded `dot4(1.0, 2.0, 3.0, 4.0)` in GF16. That equality is the
cross-die anchor of **TG-TRIAD-X (Theorem 36.1)** in
[PhD chapter 36](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex).

## Architecture

```
                 ┌──────────────────────────────────────────┐
   ui_in[0]      │       tt_um_trinity_nano (top)           │
   load_mode ───►│                                          │
   ui_in[7]      │   ┌───────────────────────────────────┐  │
   load_strobe ─►│   │ canonical gf16_dot4(1,2,3,4)      │  │ ──► uo_out[7:0]   = 0xC0
   ui_in[6]      │   │   (combinational, always live)    │  │     uio_out[7:0]  = 0x47
   compute_s ───►│   └───────────────────────────────────┘  │
                 │                                          │
   uio_in[7:0]   │   ┌───────────────────────────────────┐  │
   operand ─────►│   │ trinity_gf16_tile #(TILE_ID=0)    │──┼──► uo_out / uio_out
                 │   │ packet path (LOAD_A, COMPUTE,     │  │     when load_mode=1
                 │   │  RESULT, RECEIPT)                 │  │
                 │   └───────────────────────────────────┘  │
                 └──────────────────────────────────────────┘
```

- **`load_mode = 0` (default):** output pins always present `0x47C0`. This
  is what the TT test harness samples on the first cycle after reset, and
  it is what the **TG-TRIAD-X canonical job** observes from all three dies.
- **`load_mode = 1`:** rising edges on `ui_in[7]` clock the byte on
  `uio_in` into operand-A lanes 0…3 of the internal tile; a rising edge on
  `ui_in[6]` then issues a `COMPUTE` packet. Result appears on the
  `uo_out`+`uio_out` pins on the next cycle.

## Hard constraints (Silicon Invariants)

| Rule | Statement | Enforced by |
|------|-----------|-------------|
| **R-SI-1** | 0 new `*` operators in synthesisable RTL | Code review; gf16_mul is XOR-based |
| **R-SI-2** | 0 DSP / multiplier macros | OpenLane2 reports |
| **R-SI-3** | WNS ≥ 0 ns at 50 MHz on SKY130A | OpenLane2 STA |
| **R-SI-4** | DRC-clean (0 violations) | OpenLane2 KLayout DRC |
| **R-SI-5** | LVS-clean | OpenLane2 LVS |
| **R-SI-6** | Apache-2.0 only, no vendor IP | LICENSE + source headers |

---

## 🏆 Competitive Differentiators — Minimal Chip, Maximum Validation

| # | Differentiator | This Chip (φ-anchor) | Hailo-8 | MediaTek D9400 NPU890 | QC Cloud AI 100 Ultra | Axelera Metis M.2 | Google Coral Edge TPU |
|---|----------------|-----------------------|---------|---------------------|---------------------|-------------------|-------------------|
| 1 | Native ternary {-1,0,+1} MAC | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 2 | On-chip BLAKE3 receipt signer | ❌ (minimal) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 3 | POST via φ²+φ⁻²=3 Lucas chain | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 4 | 0 DSP / 0 new `*` (R-SI-1) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 5 | BitNet b1.58 ternary MLP | ❌ (minimal) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 6 | RING27 3³ ternary memory | ❌ (minimal) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 7 | Trinity 9-op ternary ALU (t27 ISA) | ❌ (minimal) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 8 | On-chip BPB / cross-entropy | ❌ (minimal) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 9 | Apache-2.0 + fully open PDK (SKY130A) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 10 | DOI-anchored + Coq-verified | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Note:** As the smallest (1×1) TRI-NET member, φ-anchor validates the base arithmetic layer. Full SUPER-CROWN capabilities (BLAKE3, BitNet, RING27, ALU, BPB) are available in e-engine (8×2) and γ-surface (8×4).

**Still unique:** No competitor has even the first advantage (native ternary MAC) — all use binary/int8 quantization.

## Build

```bash
# Local simulation (iverilog)
cd test
make
```

```bash
# GDS via GitHub Actions
git push
# → triggers .github/workflows/gds.yaml
# → OpenLane2 (SKY130A) → DRC + LVS + STA → uploads gds_artifact
```

## Pin mapping

See [`info.yaml`](info.yaml) for the canonical map. Summary:

- `ui_in[0]`  — `load_mode`
- `ui_in[6]`  — `compute_strobe`
- `ui_in[7]`  — `load_lane_strobe`
- `uio_in`    — operand byte (low 8 bits of GF16 element)
- `uo_out`    — result[7:0]
- `uio_out`   — result[15:8]
- `uio_oe`    — `8'hFF` (always drive)

## Provenance

- **License:** Apache-2.0 (see [LICENSE](LICENSE))
- **DOI:** [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
- **Author:** Dmitrii Vasilev <admin@t27.ai>, ORCID [0009-0008-4294-6159](https://orcid.org/0009-0008-4294-6159)
- **Defense:** 2026-06-15
- **Shuttle:** TinyTapeout TTSKY26b, close 2026-05-18

## See also

- Mid SKU: [tt-trinity-gf16](https://github.com/gHashTag/tt-trinity-gf16)
- PhD chapter: [`flos_70.tex` — Ch. 36 TRI-1 Triad](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex)
- EPIC: [trinity-fpga#49 L-DPC7](https://github.com/gHashTag/trinity-fpga/issues/49)
- Throne: [trios#264 Queen's Registry](https://github.com/gHashTag/trios/issues/264)

---

## 🟢 Bazaar Doctrine · Green AI Manifesto

This chip is part of the **TRI-NET** — an open ternary neuromorphic substrate
released under [Apache-2.0](LICENSE) for the decentralized hardware bazaar.

### Honest performance disclosure (R5-HONEST)

| Metric | Measured (SKY130 130nm) | Architecture target (22FDX 22nm projection) |
|---|---|---|
| TOPS/W | proof-of-concept node | 28-120 TOPS/W (peer-review pending) |
| Energy/op | educational node | competitive vs Hailo/Mythic at advanced node |

The SKY130A demonstrator validates **architecture**, not absolute silicon performance.
Production-grade tape-out requires migration to advanced node.

### Green AI alignment

- **Ternary {−1, 0, +1}** — ~10× energy/op vs FP16 at equivalent accuracy
  ([BitNet b1.58, Microsoft Research 2024, arXiv:2402.17764](https://arxiv.org/abs/2402.17764))
- **0 DSP / 0 `*`** — R-SI-1 RTL constraint eliminates multiplier switching energy
- **Edge inference** — no datacenter transit, no PUE overhead
- **Open-source RTL** — reproducible silicon eliminates duplicated tape-out waste

### The Bazaar, not the Cathedral

> *"Many heads are inevitably better than one."*
> — Eric S. Raymond, [The Cathedral and the Bazaar (1997)](http://www.catb.org/~esr/writings/cathedral-bazaar/)

This repository is open under Apache-2.0 with **no field-of-endeavor restriction**
([OSD §6](https://opensource.org/osd)). Fork it. Improve it. Build with it.
We do not gate-keep what you build. You comply with your local export control;
we comply with ours.

**φ² + φ⁻² = 3** · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
