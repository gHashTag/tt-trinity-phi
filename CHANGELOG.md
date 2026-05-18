# Changelog — TRI-1 Phi (φ-anchor)

All notable changes to the **tt-trinity-phi** project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- `docs/API.md` — Complete API documentation with module interfaces
- `docs/ARCHITECTURE.md` — ASCII architecture diagrams (system overview, pin mapping, data flow, POST flow)
- `docs/COMPARISON.md` — Cross-chip comparison matrix (phi/euler/gamma)
- Performance benchmarks section in README with throughput, latency, area, power tables
- Additional testbenches for quantization modules

### Changed
- Updated README with unified badge order and TRI-NET cross-references section
- Improved test coverage across all quantization modules

---

## [TTSKY26b-submit] — 2026-05-17

### Tape-out
- Submitted to Tiny Tapeout SKY 26b shuttle (close: 2026-05-18 UTC)
- Allocation: **1×1** tiles (smallest SKU — golden foundation, must close)
- Cross-die anchor: dot4(1,2,3,4) = 0x47C0 — TG-TRIAD-X ledger (Theorem 36.1)

### Fixed
- **Canonical anchor stability** — POST status output gated behind `ui_in[3]&ui_in[2]`; prevents spurious POST status overwriting canonical 0x47C0 on default outputs
- **R-SI-1 compliance** — zero `*` operators in synthesisable RTL; all multiplication replaced by GF16 LUT-based primitives (`gf16_mul.v`)
- **cocotb Makefile** — resolved `$(MAKEFILE_LIST)` expansion bug that caused test runner failures in CI

### Added
- `docs/info.md` — Tiny Tapeout submit requirement (project description, pin mapping, usage instructions)

### Verified
- All 5 CI workflows green: t27 Format, R-SI-1 no-star, RTL & Cocotb, FPGA Synthesis, GDS
- `tt_submission` artifact validated
- Cross-die canonical anchor 0x47C0 = dot4(1,2,3,4) confirmed on {uio_out, uo_out} at reset
- Lucas POST proving φ²+φ⁻²=3 (L₂…L₇ chain) verified in simulation

---

<!-- DOI: 10.5281/zenodo.19227877 — previous version -->
<!-- Siblings: tt-trinity-euler (8×2, 16 tiles) · tt-trinity-gamma (8×4, 32 tiles) -->