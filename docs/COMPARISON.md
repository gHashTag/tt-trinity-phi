# TRI-NET Cross-Chip Comparison

## Overview

TRI-NET is a family of three sacred-constant anchored neuromorphic chips:

| Chip | Size | Sacred Constant | Tile Count | TOPS/W Baseline | TOPS/W with AVS |
|------|------|-----------------|------------|-----------------|-----------------|
| φ-anchor (phi) | 1×1 | φ (golden ratio) | 1 | 75 | 405 |
| e-engine (euler) | 8×2 | e (Euler's number) | 16 | 104 | 405 |
| γ-surface (gamma) | 8×4 | γ (Euler-Mascheroni) | 32 | 104 | 405 |

## Feature Matrix

| Feature | φ | e | γ |
|---------|---|---|---|
| **Form Factor** | 1×1 | 8×2 | 8×4 |
| **Density** | 60% | ~70% | ~80% |
| **Tile Count** | 1 | 16 | 32 |
| **Processing Elements** | 1 | 16 | 20 (mesh) + 8 (cortex) |
| **Neuromorphic Cortex** | ❌ | ❌ | ✅ 8 columns |
| **D2D Mesh** | ✅ 4-port stub | ✅ 2×2 router | ✅ 4-port holo router |
| **LAYER-FROZEN Gate** | ❌ | ❌ | ✅ (PhD Thm 36.1 R18) |
| **SUPER-CROWN Modules** | 12 | 18 | 24 |
| **CLARA Safety Gaps** | Gap-4 | Gaps 1-10 | Gaps 1-4 |

## SUPER-CROWN Modules

| Module | φ | e | γ | Description |
|--------|---|---|---|-------------|
| φ-anchor POST | ✅ | ✅ | ✅ | Lucas chain verification |
| Lucas ROM | ✅ | ✅ | ✅ | L₂..L₇ addressable |
| VSA Matmul 8×8 | ❌ | ✅ | ✅ | Ternary matmul |
| VSA Matmul 16×16 | ❌ | ❌ | ✅ | JEPA-T tier |
| BitNet Encoder | ❌ | ✅ | ✅ | b1.58 ternary encoder |
| BLAKE3 Anchor | ❌ | ✅ | ✅ | DePIN receipt signer |
| BPB Counter | ❌ | ✅ | ✅ | Shannon entropy |
| BPB Guard | ❌ | ✅ | ✅ | Lower-bound guard |
| Multi-tile Receipt | ❌ | ✅ | ✅ | Receipt aggregator |
| CRC-32 Receipt | ❌ | ✅ | ✅ | CRC generator |
| ALU-9 Decoder | ❌ | ✅ | ✅ | Ternary ALU |
| RING27 Memory | ❌ | ✅ | ✅ | Ternary memory |
| HWRNG LFSR | ✅ | ✅ | ✅ | Die-unique nonce |
| φ-PLL Div | ❌ | ✅ | ✅ | Fractional divider |
| WB Status Reg | ❌ | ✅ | ✅ | Wishbone status |
| Wishbone Full | ❌ | ✅ | ✅ | Wishbone peripheral |
| Cassini POST | ❌ | ❌ | ✅ | Extended Lucas |
| PLRM Counter | ❌ | ❌ | ✅ | Mutual-exclusion monitor |
| NCA Entropy Monitor | ❌ | ❌ | ✅ | Entropy band |
| Strobe Seed Guard | ❌ | ❌ | ✅ | Forbidden seed |
| Φ-Distance Oracle | ❌ | ❌ | ✅ | 360-entry LUT |
| Crown47 ROM | ✅ | ✅ | ✅ | 47 Trinity constants |
| Sacred ROM | ✅ | ✅ | ✅ | 75 PhD constants |
| Trinity Friend/Foe | ✅ | ✅ | ✅ | Cross-die handshake |
| Holo LUT PE | ❌ | ❌ | ✅ | FHRR hypervectors |

## PhD-Anchored Monitors

| Monitor | φ | e | γ | Description |
|---------|---|---|---|-------------|
| cassini_post | ❌ | ❌ | ✅ | Cassini identity |
| plrm_counter | ❌ | ❌ | ✅ | PLRM arbitration |
| bpb_lower_bound_guard | ❌ | ❌ | ✅ | BPB lower bound |
| nca_entropy_monitor | ❌ | ❌ | ✅ | NCA entropy band |
| strobe_seed_guard | ❌ | ❌ | ✅ | Forbidden seed |
| phi_distance_oracle | ❌ | ❌ | ✅ | Φ-distance LUT |

## CLARA AI Safety Gaps

| Gap | Module | φ | e | γ | Description |
|-----|--------|---|---|---|-------------|
| Gap-1 | redteam_filter | ❌ | ✅ | ✅ | Adversarial input filtering |
| Gap-2 | k3_alu | ❌ | ✅ | ✅ | Ternary logic unit |
| Gap-3 | datalog_engine_mini | ❌ | ✅ | ✅ | Mini Datalog reasoning |
| Gap-4 | restraint_ctrl | ✅ | ✅ | ✅ | Bounded rationality |
| Gap-5 | explainability_unit | ❌ | ✅ | ❌ | Computation trace |
| Gap-6 | asp_solver_mini | ❌ | ✅ | ❌ | ASP solver |
| Gap-7 | composition_kernel | ❌ | ✅ | ❌ | Safe function composition |
| Gap-8 | proof_trace_writer | ❌ | ✅ | ❌ | Formal proof trace |
| Gap-9 | sat_solver_mini | ❌ | ✅ | ❌ | SAT solver |
| Gap-10 | audit_log_ring_buffer | ❌ | ✅ | ❌ | Audit trail |

## Power Management

| Module | φ | e | γ | Description |
|--------|---|---|---|-------------|
| AVS-48 | ❌ | ❌ | ❌ | 48-island controller (legacy) |
| AVS-96 | ✅ | ✅ | ✅ | 96-island controller |
| FBB Active Path | ✅ | ✅ | ✅ | Forward body bias |
| Purkinje Thermal Gate | ✅ | ✅ | ✅ | Thermal monitoring |
| Subth Clock | ❌ | ❌ | ❌ | Subthreshold clock |

## Quantization Support

| Quantizer | φ | e | γ | Input → Output |
|-----------|---|---|---|----------------|
| Int4 Quantizer | ✅ | ✅ | ✅ | FP16 → Int4 |
| Int8 Quantizer | ✅ | ✅ | ✅ | FP16 → Int8 |
| NF4 Quantizer | ✅ | ✅ | ✅ | FP16 → NF4 (QLoRA) |
| FP8 E4M3 Quantizer | ✅ | ✅ | ✅ | FP16 → FP8 (4 exp, 3 mant) |
| FP8 E5M2 Quantizer | ✅ | ✅ | ✅ | FP16 → FP8 (5 exp, 2 mant) |
| Posit16 Quantizer | ✅ | ✅ | ✅ | FP16 → Posit16 |

## GF16 Arithmetic

| Operation | φ | e | γ | Description |
|-----------|---|---|---|-------------|
| GF16 Add | ✅ | ✅ | ✅ | XOR-based |
| GF16 Mul | ✅ | ✅ | ✅ | Shift-add partial products |
| GF16 Dot4 | ✅ | ✅ | ✅ | 4-vector dot product |
| GF16 Dot4 Sparse | ❌ | ✅ | ✅ | Sparse dot product |
| GF16 Dot8 | ❌ | ❌ | ✅ | 8-vector dot product |
| GF4-GF256 Add | ✅ | ✅ | ✅ | Multiple field sizes |

## Performance Comparison

### Area (approximate)

| Chip | Cortex | Mesh | SUPER-CROWN | CLARA | Total |
|------|--------|------|-------------|-------|-------|
| φ | - | ~100 | ~400 | ~100 | ~600 cells |
| e | - | ~2500 | ~2500 | ~1500 | ~6500 cells |
| γ | ~4100 | ~2000 | ~2500 | ~500 | ~9100 cells |

### Power

| Chip | Baseline | With AVS-96 | Savings |
|------|----------|-------------|---------|
| φ | 75 mW | 12 mW | -84% |
| e | 480 mW | 56 mW | -88% |
| γ | 480 mW | 56 mW | -88% |

### Throughput

| Chip | GF16 MAC/cycle | Spikes/cycle | TOPS @ 50 MHz |
|------|----------------|--------------|----------------|
| φ | 1 | - | 0.05 |
| e | 16 | - | 0.8 |
| γ | 20 | 8 | 1.0 + 0.4 (spikes) |

### TOPS/W

| Chip | Baseline | With AVS-96 | Boost Factor |
|------|----------|-------------|---------------|
| φ | 75 | 405 | 5.4× |
| e | 104 | 405 | 3.9× |
| γ | 104 | 405 | 3.9× |

## Use Case Recommendations

| Use Case | Best Chip | Reason |
|----------|-----------|--------|
| Minimal footprint / verification | φ | Smallest, canonical anchor |
| AI Safety research | e | Full CLARA gaps (1-10) |
| Neuromorphic inference | γ | Cortex + BitNet + D2D |
| Batch processing | e | 16 tiles, high throughput |
| Spike-based computing | γ | LIF dynamics, D2D sync |
| Energy-constrained edge | φ | Lowest power (12 mW with AVS) |

## Compatibility Matrix

| Feature | φ | e | γ | Cross-Use |
|---------|---|---|---|-----------|
| D2D to φ | - | ✅ | ✅ | Any chip can detect φ |
| D2D to e | ✅ | - | ✅ | Any chip can detect e |
| D2D to γ | ✅ | ✅ | - | Any chip can detect γ |
| Packet protocol | ✅ | ✅ | ✅ | TRN compatible |
| CROWN47 ROM | ✅ | ✅ | ✅ | Same constants |
| Sacred ROM | ✅ | ✅ | ✅ | Same constants |
| AVS-96 | ✅ | ✅ | ✅ | Same controller |

## Shuttle Submission

| Chip | Shuttle | Status |
|------|---------|--------|
| φ | TTSKY26b | ✅ Submitted |
| e | TTSKY26b | ✅ Submitted |
| γ | TTSKY26b | ✅ Submitted |

## References

- Sacred Anchor: φ² + φ⁻² = 3 — DOI 10.5281/zenodo.19227877
- R-SI-1 Compliance: Zero multiplication operators in RTL
- Verilog-2005: No SystemVerilog, no indexed part-selects
- TTSKY26b: TinyTapeout shuttle, sky130A process