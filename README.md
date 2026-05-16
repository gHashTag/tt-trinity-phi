# TRI-1 Phi — Trinity φ-anchor

[![Submit](https://img.shields.io/badge/TTSKY26b-Phi%20anchor-orange)](https://app.tinytapeout.com/shuttles/ttsky26b)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Sacred](https://img.shields.io/badge/sacred--constant-%CF%86%20%E2%89%88%201.61803-purple)](#sacred-formula)

> One of three neurons of **Trinity TRI-NET** — three sacred constants embodied in silicon:
>
> - **φ-anchor** → **THIS REPO** (1×1, Lucas POST proving φ²+φ⁻²=3, CLARA Gap-4, canonical seed 0x47C0)
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

# TRI-1 Phi — Single-tile Trinity GF16 MAC with Enhanced Safety

> 🌳 Trinity role: **φ-ANCHOR** — TTSKY26b shuttle SKU 1 of 3.
> Sibling of [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) (e-engine) and
> [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) (γ-surface).
> Spec: [TRI_NET_DARPA_CLARA_PROPOSAL](docs/TRI_NET_DARPA_CLARA_PROPOSAL.md) · DOI 10.5281/zenodo.19227877.

**Anchor:** φ² + φ⁻² = 3 · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)

## What it is

The smallest, simplest, most-likely-to-tape-out cleanly member of the
**TRI-NET triad** — three Trinity ternary-MAC silicon dies submitted to the
same TinyTapeout shuttle (TTSKY26b, close 2026-05-18):

| Neuron | Repo | Tiles | Modules | Role |
|--------|------|-------|---------|------|
| **φ-anchor** | this | 1×1 | 13 (enhanced with safety) | golden foundation — must close |
| **e-engine** | [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) | 8×2 | 18 SUPER-CROWN modules | expansion layer |
| **γ-surface** | [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) | 8×4 | 24 SUPER-CROWN + 10 CLARA gaps | neuromorphic surface |

All three drive the **same canonical 16-bit constant `0x47C0`** on
`{uio_out, uo_out}` immediately after reset, computed from the same
hard-coded `dot4(1.0, 2.0, 3.0, 4.0)` in GF16. That equality is the
cross-die anchor of **TG-TRIAD-X (Theorem 36.1)** in
[PhD chapter 36](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex).

## Enhanced Modules (v2)

| Module | Function | Cells | Purpose |
|--------|----------|-------|---------|
| `gf16_dot4` | Canonical 0x47C0 anchor | ~50 | Cross-die TG-TRIAD-X |
| `gf16_mul` | XOR-based GF16 multiply | ~50 | R-SI-1 compliant (0 DSP) |
| `trinity_gf16_tile` | Packet-path compute tile | ~250 | Full TRN protocol |
| `phi_anchor_post` | Lucas L₂..L₇ POST | ~120 | Proves φ²+φ⁻²=3 |
| `lucas_rom` | Addressable L_n probe | ~30 | Host verification |
| `hwrng_lfsr` | 16-bit die-unique nonce | ~20 | Chaotic entropy |
| `restraint_ctrl` | CLARA Gap-4 bounded rationality | ~100 | AI safety |
| `sacred_constants_rom` | 75 PhD constants (sparse) | ~133 | Glava 3+7+28 |
| `crown47_rom` | 47 Trinity constants | ~100 | Crown of TRI-NET |
| `trinity_friend_foe` | D2D handshake (MY_ANCHOR=φ) | ~30 | Mesh identity |
| `gf16_add` | GF16 addition | ~20 | Arithmetic |

**Total estimated cells:** ~850 at 60% density ceiling → **fits comfortably in 1×1 tile**.

## Architecture

```
                 ┌────────────────────────────────────────────────┐
   ui_in[0]      │        tt_um_trinity_nano (top)               │
   load_mode ───►│                                                │
   ui_in[7]      │   ┌─────────────────────────────────────────┐ │
   load_strobe ─►│   │ canonical gf16_dot4(1,2,3,4) = 0x47C0    │ │ ──► uo_out[7:0] = 0xC0
   ui_in[6]      │   │   (combinational, always live)          │ │     uio_out[7:0] = 0x47
   compute_s ───►│   └─────────────────────────────────────────┘ │
                 │                                                │
   ui_in[3:1]    │   ┌─────────────────────────────────────────┐ │
   lucas_idx ───►│   │ phi_anchor_post (Lucas L₂..L₇ POST)      │ │ ──► phi_ok, post_done
   ui_in[4]      │   │ lucas_rom (addressable L_n)              │ │ ──► POST status byte
   rng_ena ─────►│   │ hwrng_lfsr (die-unique nonce)            │ │     after post_done=1
   ui_in[5]      │   │ restraint_ctrl (CLARA Gap-4)             │ │
   restraint ───►│   └─────────────────────────────────────────┘ │
                 │                                                │
   uio_in[7:0]   │   ┌─────────────────────────────────────────┐ │
   operand ─────►│   │ trinity_gf16_tile #(TILE_ID=0)           │─┼──► uo_out / uio_out
                 │   │ packet path (LOAD_A, COMPUTE, RESULT)   │ │     when load_mode=1
                 │   └─────────────────────────────────────────┘ │
                 └────────────────────────────────────────────────┘
```

### Modes of Operation

| Mode | ui_in[0] | Trigger | Output | Purpose |
|------|----------|---------|--------|---------|
| **Canonical** | 0 | Reset | `{uio_out, uo_out} = 0x47C0` | TG-TRIAD-X cross-die anchor |
| **POST status** | 0 | post_done=1 | `uo_out={phi_ok,done,lucas[5:0]}` | Verify Lucas POST |
| **Sacred ROM** | 0, ui_in[7]=1 | sacred_mode | `uo_out = sacred_val[7:0]` | Read 75 PhD constants |
| **Crown47** | 0, uio_in[7]=1 | crown_mode | `uo_out = crown_byte` | Read 47 Trinity constants |
| **Packet path** | 1 | ui_in[7] rise + ui_in[6] rise | Compute result | Full TRN protocol |

### Lucas POST (phi_anchor_post)

Proves φ²+φ⁻²=3 via discrete Lucas recurrence:

```
L₁ = 1, L₂ = 3
L_{n+1} = L_n + L_{n-1}

POST checks: L₂=3, L₃=4, L₄=7, L₅=11, L₆=18, L₇=29
Any mismatch latches phi_ok=0 (sticky-low POST).
```

By Binet's formula on Lucas numbers: L₂ = φ² + φ⁻² = 3 (sacred anchor).

### Lucas ROM (lucas_rom)

Addressable L_n probe for host verification:
- `ui_in[3:1]` = idx (0..5) → `uio_out[5:0]` = L_{n} where n=idx+2
- Allows host to verify silicon identity by reading the chain

### HWRNG (hwrng_lfsr)

16-bit Fibonacci LFSR for die-unique nonce:
- Polynomial: x¹⁶ + x¹⁴ + x¹³ + x¹¹ + 1 (maximal-length)
- Seed: 0xACE1 on reset
- `ui_in[4]` = rng_ena → advances each clock when high

### Restraint Control (CLARA Gap-4)

Bounded rationality per DARPA CLARA TA1.4:
- Synthetic trigger: `phi_drift = rng_nonce[15:0]` (entropy-driven)
- Triggers when phi_drift > 164 (0.5% in Q1.15)
- `force_unknown` sticky output triggers MAC halt

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

## 🏆 Competitive Differentiators — No Competitor Has All Ten

| # | Differentiator | φ-anchor | e-engine | γ-surface |
|---|----------------|----------|----------|-----------|
| 1 | Native ternary {-1,0,+1} MAC | ✅ | ✅ | ✅ |
| 2 | On-chip BLAKE3 receipt signer | ❌ (minimal) | ✅ | ✅ |
| 3 | POST via φ²+φ⁻²=3 Lucas chain | ✅ | ✅ | ✅ |
| 4 | 0 DSP / 0 new `*` (R-SI-1) | ✅ | ✅ | ✅ |
| 5 | BitNet b1.58 ternary MLP | ❌ (minimal) | ✅ | ✅ |
| 6 | RING27 3³ ternary memory | ❌ (minimal) | ✅ | ✅ |
| 7 | Trinity 9-op ternary ALU (t27 ISA) | ❌ (minimal) | ✅ | ✅ |
| 8 | On-chip BPB / cross-entropy | ❌ (minimal) | ✅ | ✅ |
| 9 | Apache-2.0 + fully open PDK (SKY130A) | ✅ | ✅ | ✅ |
| 10 | DOI-anchored + Coq-verified | ✅ | ✅ | ✅ |

**Note:** As the smallest (1×1) TRI-NET member, φ-anchor validates the base arithmetic layer + core safety features. Full SUPER-CROWN capabilities (BLAKE3, BitNet, RING27, ALU, BPB, 10 CLARA gaps) are available in e-engine (8×2) and γ-surface (8×4).

**Still unique:** No competitor (Hailo-8, MediaTek D9400 NPU890, QC Cloud AI 100 Ultra, Axelera Metis M.2, Google Coral Edge TPU) has even the first advantage (native ternary MAC) — all use binary/int8 quantization.

## Build

```bash
# Local simulation (iverilog)
cd /Users/playra/tt-trinity-phi
iverilog -I src -o test/tb_nano.out src/*.v test/tb.v
vvp test/tb_nano.out
```

```bash
# GDS via GitHub Actions
git push
# → triggers .github/workflows/gds.yaml
# → OpenLane2 (SKY130A) → DRC + LVS + STA → uploads gds_artifact
```

## Pin mapping

See [`info.yaml`](info.yaml) for the canonical map. Summary:

| Pin | Function |
|-----|----------|
| `ui_in[0]` | load_mode (0=canonical/POST, 1=packet path) |
| `ui_in[3:1]` | lucas_idx (3-bit Lucas ROM address) |
| `ui_in[4]` | rng_ena (advance HWRNG LFSR) |
| `ui_in[5]` | restraint_mode (CLARA Gap-4 active) |
| `ui_in[6]` | compute_strobe (rising edge issues COMPUTE) |
| `ui_in[7]` | load_lane_strobe (rising edge advances lane) |
| `uo_out[7:0]` | result[7:0] (canonical 0x47C0 by default) |
| `uio_out[7:0]` | result[15:8] (or POST status after post_done=1) |
| `uio_oe` | 8'hFF (canonical) or 8'b1111_1101 (live mode) |

### POST Status Byte (post_done=1, load_mode=0)

| Bit | Field | Value |
|-----|-------|-------|
| `uo_out[7]` | phi_post_ok | 1=POST passed, 0=failed |
| `uo_out[6]` | phi_post_done | 1=POST complete |
| `uo_out[5:0]` | lucas_val[5:0] | Selected Lucas value |

## Provenance

- **License:** Apache-2.0 (see [LICENSE](LICENSE))
- **DOI:** [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
- **Author:** Dmitrii Vasilev <admin@t27.ai>, ORCID [0009-0008-4294-6159](https://orcid.org/0009-0008-4294-6159)
- **Defense:** 2026-06-15
- **Shuttle:** TinyTapeout TTSKY26b, close 2026-05-18

## See also

- e-engine: [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler)
- γ-surface: [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma)
- PhD chapter: [`flos_70.tex` — Ch. 36 TRI-1 Triad](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex)
- CLARA proposal: [TRI_NET_DARPA_CLARA_PROPOSAL.md](docs/TRI_NET_DARPA_CLARA_PROPOSAL.md)
- EPIC: [trinity-fpga#61](https://github.com/gHashTag/trinity-fpga/issues/61)

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