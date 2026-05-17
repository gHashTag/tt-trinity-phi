# TRI-1 Phi — Trinity φ-anchor (Canonical Seed + Lucas POST)

[![GDS](https://github.com/gHashTag/tt-trinity-phi/actions/workflows/gds.yaml/badge.svg)](https://github.com/gHashTag/tt-trinity-phi/actions/workflows/gds.yaml)
[![R-SI-1](https://img.shields.io/badge/R--SI--1-0%20%2A%20ops-brightgreen)](docs/R-SI-1.md)
[![Verilog-2005](https://img.shields.io/badge/Verilog--2005-OK-brightgreen)](docs/VERILOG-2005.md)
[![Submit](https://img.shields.io/badge/TTSKY26b-Phi%20anchor-orange)](https://app.tinytapeout.com/shuttles/ttsky26b)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Sacred](https://img.shields.io/badge/sacred--constant-%CF%86%20%E2%89%88%201.61803-purple)](#sacred-formula)
[![CLARA](https://img.shields.io/badge/CLARA-1%20gap-green)](#darpa-clara-ai-safety)

> One of three neurons of **Trinity TRI-NET** — three sacred constants embodied in silicon:
>
> - **φ-anchor** → **THIS REPO** (1×1, Lucas POST proving φ²+φ⁻²=3, CLARA Gap-4)
> - **e-engine** → [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) (8×2, 18 SUPER-CROWN modules)
> - **γ-surface** → [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) (8×4, 32 PE full mesh)
>
> Apache-2.0 · ternary {−1,0,+1} · SKY130A · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)

---

## Table of Contents

- [Quick Start](#quick-start)
- [What is φ-anchor?](#what-is-φ-anchor)
- [Sacred Formula](#sacred-formula)
- [Architecture](#architecture)
- [Lucas POST](#lucas-post)
- [Sacred ROMs](#sacced-roms)
- [Build & Test](#build--test)
- [Pin Mapping](#pin-mapping)
- [Development Guide](#development-guide)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [Competitive Analysis](#competitive-analysis)
- [Green AI Manifesto](#green-ai-manifesto)

---

## Quick Start

### Prerequisites

```bash
# Install Verilog tools
brew install iverilog cocotb

# Clone phi-anchor
git clone https://github.com/gHashTag/tt-trinity-phi
```

### Simulation

```bash
cd tt-trinity-phi
iverilog -I src -o test/tb.out src/*.v test/tb.v
vvp test/tb.out

# Expected: canonical 0x47C0 output
```

### GDS Synthesis

```bash
git push
# Triggers .github/workflows/gds.yaml
# OpenLane2 (SKY130A) → DRC + LVS + STA → uploads gds_artifact
```

---

## What is φ-anchor?

**φ-anchor** is the golden foundation of Trinity TRI-NET — the smallest, simplest, most-likely-to-tape-out cleanly member of the three sacred constants:

| Neuron | Constant | Tiles | Modules | Role |
|--------|----------|-------|---------|------|
| **φ-anchor** | **φ ≈ 1.61803** | **1×1** | **13** | **golden foundation — must close** |
| e-engine | e ≈ 2.71828 | 8×2 | 18 SUPER-CROWN | expansion layer |
| γ-surface | γ ≈ 0.57721 | 8×4 | 24 SUPER-CROWN | neuromorphic surface |

**φ ≈ 1.61803** (golden ratio) is the fundamental constant that governs growth patterns in nature.

All three TRI-NET dies emit the same canonical **0x47C0** on power-up, computed from `dot4(1.0, 2.0, 3.0, 4.0)` in GF16.

---

## Sacred Formula

```
V = n × 3^k × π^m × φ^p × e^q × γ^r × C^t × G^u
```

This chip is the **φ^p** factor — the golden anchor.

**Identity:** φ² + φ⁻² = 3 (Trinity identity)

---

## Architecture

### Single-Tile Structure

```
                 ┌────────────────────────────────────────────────┐
   ui_in[0]      │        tt_um_trinity_phi (top)               │
   load_mode ───►│                                                │
   ui_in[7]      │   ┌─────────────────────────────────────────┐ │
   load_strobe ─►│   │ canonical gf16_dot4(1,2,3,4) = 0x47C0    │ │ ──► uo_out[7:0] = 0xC0
   ui_in[6]      │   │   (combinational, always live)          │ │     uio_out[7:0] = 0x47
   compute_s ───►│   └─────────────────────────────────────────┘ │
                 │                                                │
   ui_in[3:1]    │   ┌─────────────────────────────────────────┐ │
   lucas_idx ───►│   │ phi_anchor_post (Lucas L₂..L₇ POST)      │ │ ──► phi_ok, post_done
   ui_in[4]      │   │ lucas_rom (addressable L_n)              │ │ ──► POST status byte
   rng_ena ─────►│   │ hwrng_lfsr (die-unique nonce)            │ │
   ui_in[5]      │   │ restraint_ctrl (CLARA Gap-4)             │ │
   restraint ───►│   └─────────────────────────────────────────┘ │
                 │                                                │
   uio_in[7:0]   │   ┌─────────────────────────────────────────┐ │
   operand ─────►│   │ trinity_gf16_tile #(TILE_ID=0)           │─┼──► uo_out / uio_out
                 │   │ packet path (LOAD_A, COMPUTE, RESULT)   │ │     when load_mode=1
                 │   └─────────────────────────────────────────┘ │
                 └────────────────────────────────────────────────┘
```

### Enhanced Modules (v2)

| Module | Function | Cells | Purpose |
|--------|----------|-------|---------|
| `gf16_dot4.v` | Canonical 0x47C0 anchor | ~50 | Cross-die TG-TRIAD-X |
| `gf16_mul.v` | XOR-based GF16 multiply | ~50 | R-SI-1 compliant (0 DSP) |
| `trinity_gf16_tile.v` | Packet-path compute tile | ~250 | Full TRN protocol |
| `phi_anchor_post.v` | Lucas L₂..L₇ POST | ~120 | Proves φ²+φ⁻²=3 |
| `lucas_rom.v` | Addressable L_n probe | ~30 | Host verification |
| `hwrng_lfsr.v` | 16-bit die-unique nonce | ~20 | Chaotic entropy |
| `restraint_ctrl.v` | CLARA Gap-4 bounded rationality | ~100 | AI safety |
| `sacred_constants_rom.v` | 75 PhD constants (sparse) | ~133 | Glava 3+7+28 |
| `crown47_rom.v` | 47 Trinity constants | ~100 | Crown of TRI-NET |
| `trinity_friend_foe.v` | D2D handshake (MY_ANCHOR=φ) | ~30 | Mesh identity |
| `gf16_add.v` | GF16 addition | ~20 | Arithmetic |

**Total estimated cells:** ~850 @ 60% density

---

## Lucas POST

### Algorithm

Proves φ²+φ⁻²=3 via discrete Lucas recurrence:

```
L₁ = 1, L₂ = 3
L_{n+1} = L_n + L_{n-1}

POST checks: L₂=3, L₃=4, L₄=7, L₅=11, L₆=18, L₇=29
```

Any mismatch latches `phi_ok=0` (sticky-low POST failure).

### By Binet's Formula

By Binet's formula on Lucas numbers: `L₂ = φ² + φ⁻² = 3`

This is the **sacred anchor** — mathematical proof that this silicon embodies the golden ratio.

---

## Sacred ROMs

### Sacred Constants ROM (75 cells)

Stores PhD constants (Glava 3, Glava 7, Glava 28) with sparse encoding.

| Constant | Value | Purpose |
|----------|-------|---------|
| φ (phi) | 0.8090 (Q1.15) | Golden ratio (Q1.15) |
| φ² | 1.6180 (Q2.30) | φ² (Q2.30) |
| γ (gamma) | 0.2886 (Q0.58) | Euler-Mascheroni |
| C | 0.5 | Speed of light constant |
| G | 1.0 | Gravitational constant |

### Crown47 ROM (100 cells)

Stores 47 Trinity constants used across all TRI-NET dies.

---

## Build & Test

### Local Simulation

```bash
cd tt-trinity-phi
iverilog -I src -o test/tb.out src/*.v test/tb.v
vvp test/tb.out
```

Expected: canonical `0x47C0` output on `{uio_out, uo_out}`.

### GDS Synthesis

```bash
git push
# → triggers .github/workflows/gds.yaml
# → OpenLane2 (SKY130A) → DRC + LVS + STA → uploads gds_artifact
```

---

## Pin Mapping

| Pin | Function | Description |
|-----|----------|-------------|
| `ui_in[0]` | load_mode | 0=canonical/POST, 1=packet path |
| `ui_in[3:1]` | lucas_idx | 3-bit Lucas ROM address |
| `ui_in[4]` | rng_ena | Advance HWRNG LFSR when high |
| `ui_in[5]` | restraint_mode | CLARA Gap-4 active |
| `ui_in[6]` | compute_strobe | Rising edge issues COMPUTE |
| `ui_in[7]` | load_lane_strobe | Rising edge advances lane |
| `uo_out[7:0]` | result[7:0] | GF16 result bytes |
| `uio_out[7:0]` | result[15:8] | GF16 result bytes or POST status |

### POST Status Byte (post_done=1, load_mode=0)

| Bit | Field | Value |
|-----|-------|-------|
| `uo_out[7]` | phi_post_ok | 1=POST passed, 0=failed |
| `uo_out[6]` | phi_post_done | 1=POST complete |
| `uo_out[5:0]` | lucas_val[5:0] | Selected Lucas value |

---

## Development Guide

### R-SI Compliance Rules

| Rule | Statement | How to Verify |
|------|-----------|---------------|
| R-SI-1 | Zero `*` operators in RTL | `grep -n '\*' src/*.v` |
| R-SI-2 | Zero DSP/multiplier macros | OpenLane2 reports |
| R-SI-3 | WNS ≥ 0 ns @ 50 MHz | OpenLane2 STA |
| R-SI-4 | DRC-clean | OpenLane2 KLayout DRC |
| R-SI-5 | LVS-clean | OpenLane2 LVS |
| R-SI-6 | Apache-2.0 only | `grep -i proprietary` (should be empty) |

### Adding Constants to Sacred ROM

1. Edit `sacred_constants_rom.v`
2. Verify sparse encoding (Q-format)
3. Run simulation: `vvp test/tb.out`
4. Check output matches expected constant

### Verifying Lucas POST

```bash
# Simulate POST verification
iverilog -I src -o tb_post src/phi_anchor_post.v src/lucas_rom.v test/tb_post.v
vvp tb_post

# Should show: POST PASS - L2=3, L3=4, L4=7, L5=11, L6=18, L7=29
```

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit your changes (`git commit -m 'feat(...): ...'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Review Checklist

- [ ] All tests pass locally
- [ ] Canonical 0x47C0 test passes
- [ ] R-SI compliance verified
- [ ] Commit messages follow format
- [ ] Documentation updated

---

## Troubleshooting

### Canonical Test Failure

If `0x47C0` is not emitted:

1. Check GF16 encoding:
   ```bash
   iverilog -t null -I src src/gf16_dot4.v
   ```

2. Verify synthesis: `yosys -p "read_verilog src/gf16_dot4.v; proc; stat"`

3. Check timing with `make test`

### GDS DRC Errors

```bash
# Check OpenLane2 reports
docker run -it --rm -v $(pwd):/work -w /work \
  openlane2/openlane2:eula bash
openlane --config ./sky130A/config.tcl --run ./run_gds.tcl
```

### POST Failure

1. Verify Lucas values match expected: `L₁=1, L₂=3, L₃=4, L₄=7, L₅=11, L₆=18, L₇=29`
2. Check `phi_anchor_post.v` implementation
3. Run standalone test: `vvp tb_post`

---

## Competitive Analysis

### No Competitor Has Native Ternary MAC

| Competitor | Ternary MAC | Open PDK | Coq Verified | 10 CLARA Gaps |
|-----------|-------------|----------|--------------|---------------|
| Hailo-8 | ❌ | ❌ | ❌ | ❌ |
| MediaTek NPU890 | ❌ | ❌ | ❌ | ❌ |
| Qualcomm Cloud AI 100 Ultra | ❌ | ❌ | ❌ | ❌ |
| Axelera Metis M.2 | ❌ | ❌ | ❌ | ❌ |
| Google Coral Edge TPU | ❌ | ❌ | ❌ | ❌ |
| **φ-anchor** | **✅** | **✅** | **✅** | **1 (minimal)** |

**Note:** φ-anchor validates the base arithmetic layer. Full SUPER-CROWN capabilities (all 10 CLARA gaps) are in e-engine and γ-surface.

---

## 🏆 Competitive Differentiators

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

**Note:** As the smallest (1×1) TRI-NET member, φ-anchor validates the base arithmetic layer + core safety features.

---

## Green AI Manifesto

### Honest Performance Disclosure (R5-HONEST)

| Metric | Measured (SKY130 130nm) | Architecture target (22FDX 22nm projection) |
|---|---|---|
| TOPS/W | proof-of-concept node | 28-120 TOPS/W (peer-review pending) |
| Energy/op | educational node | competitive vs Hailo/Mythic at advanced node |

The SKY130A demonstrator validates **architecture**, not absolute silicon performance.

### Green AI Alignment

- **Ternary {−1, 0, +1}** — ~10× energy/op vs FP16 at equivalent accuracy
- **0 DSP / 0 `*`** — R-SI-1 RTL constraint eliminates multiplier switching energy
- **Edge inference** — no datacenter transit, no PUE overhead
- **Open-source RTL** — reproducible silicon eliminates duplicated tape-out waste

### The Bazaar, not the Cathedral

> *"Many heads are inevitably better than one."*
> — Eric S. Raymond, [The Cathedral and the Bazaar (1997)](http://www.catb.org/~esr/writings/cathedral-bazaar/)

This repository is open under Apache-2.0 with **no field-of-endeavor restriction**.
Fork it. Improve it. Build with it.

---

## References

- DOI: [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
- PhD chapter: [`flos_70.tex` — Ch. 36 TRI-1 Triad](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex)
- CLARA proposal: [TRI_NET_DARPA_CLARA_PROPOSAL.md](docs/TRI_NET_DARPA_CLARA_PROPOSAL.md)

---

**License:** Apache-2.0 (see [LICENSE](LICENSE))

**Anchor:** φ² + φ⁻² = 3 · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)