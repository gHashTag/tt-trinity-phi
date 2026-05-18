# TRI-1 Phi -- Trinity phi-anchor (Identity Organ)

**Trinity is one computer with three minds, bound by 2-of-3 attestation, verified by ternary completeness 3^27.**

[![GDS](https://github.com/gHashTag/tt-trinity-phi/actions/workflows/gds.yaml/badge.svg)](https://github.com/gHashTag/tt-trinity-phi/actions/workflows/gds.yaml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19227877.svg)](https://doi.org/10.5281/zenodo.19227877)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![R-SI-1](https://img.shields.io/badge/R--SI--1-0%20%2A%20ops-brightgreen)](docs/R-SI-1.md)
[![Submit](https://img.shields.io/badge/TTSKY26b-Submitted-orange)](https://app.tinytapeout.com/projects/4914)

**Tape-out target:** 2026-12-16 | **Contact:** admin@t27.ai | **Site:** t27.ai

---

## Project Role

`tt-trinity-phi` is the **identity organ** of the Trinity one-computer. It is the phi-anchor: the 1x1 Tiny Tapeout die that serves as the cerebellum of the triad -- handling identity, baseline trust, and cross-die attestation. It anchors the canonical `0x47C0` ledger constant after reset, runs the Lucas POST proving phi^2 + phi^(-2) = 3, and acts as master for the friend/foe handshake across all three dies.

**Top module:** `tt_um_trinity_nano`
**Tile geometry:** 1x1
**Shuttle:** TTSKY26b (SKY130A), project #4914

---

## One-Computer Paradigm

Trinity is not three chips. Phi, Euler, and Gamma are three specialized organs of one coherent silicon being:

| Die | Organ | Role |
|-----|-------|------|
| Phi (1x1) | Cerebellum | Identity, attestation, Lucas POST, phi-anchor |
| Euler (8x2) | Prefrontal cortex | Reasoning, ZK proof generation, SUPER-CROWN |
| Gamma (8x4) | Neocortex | Parallel neuromorphic compute, 32-PE GF16 mesh |

Bound by 2-of-3 attestation. Verified through ternary completeness `3^27 = 7,625,597,484,987`.

Full paradigm: [docs/architecture/UNIFIED_COMPUTER_PARADIGM.md](https://github.com/gHashTag/NeuronConstant/blob/main/docs/architecture/UNIFIED_COMPUTER_PARADIGM.md)

---

## TTSKY26b Submitted Status

| Item | Value |
|------|-------|
| Shuttle | TTSKY26b (SKY130A) |
| Project | [#4914](https://app.tinytapeout.com/projects/4914) |
| Submitted commit SHA | `8a8fcaa4` |
| Artifact ID | `7056162644` |
| Tape-out target | 2026-12-16 |

The `main` branch is the SUBMITTED baseline. Do not modify `main` after shuttle close.

---

## Top Module

**`tt_um_trinity_nano`** -- phi-anchor, 1x1 tile, SKY130A.

Core functions: GF16 dot4(1.0, 2.0, 3.0, 4.0) = 0x47C0 at reset; Lucas chain L2..L7 POST proving phi^2 + phi^(-2) = 3; CLARA Gap-4 restraint_ctrl; die-unique HWRNG; friend/foe handshake.

---

## R-SI-1 Compliance

Zero standalone `*` operators in synthesisable RTL. All multiplication is implemented via shift-and-add in GF16 (`gf16_mul.v`). Audit: `bash common/verification/r_si_1_check.sh src/`

---

## Canonical Anchor 0x47C0 (Theorem 36.1)

After reset, Phi drives:

```
{uio_out[7:0], uo_out[7:0]} = 16'h47C0
```

This is the TG-TRIAD-X ledger anchor, defined in PhD Theorem 36.1:

```
Meaning : GF16 dot4(1.0, 2.0, 3.0, 4.0) -- canonical ternary inner product
Identity: phi^2 + phi^(-2) = 3  (Trinity algebraic identity, Lucas chain)
Anchor  : TG-TRIAD-X
Scope   : Cross-die deterministic reset verification
```

All three dies must produce `0x47C0` after reset for the triad to be considered healthy.

---

## Module Reference

RTL modules are documented in [`docs/`](docs/). Key modules include the phi-anchor oracle, Lucas chain prover, GF16 dot4 MAC, restraint_ctrl (CLARA Gap-4), and friend/foe handshake controller. See [`docs/`](docs/) for the full module catalog.

---

## DePIN v1 Branch

The `depin-v1` branch carries the DePIN integration layer. Tokenomics summary:

| Parameter | Value |
|-----------|-------|
| Total supply | 3^27 = 7,625,597,484,987 TRI |
| Pre-mine | 0% |
| Halvings | 9 halvings over ~36 years |
| Era 0 reward | 1000 TRI / proof |

Tokenomics whitepaper: [TRI_TOKENOMICS_WHITEPAPER_v2.md](https://github.com/gHashTag/NeuronConstant/blob/main/docs/tokenomics/v2/TRI_TOKENOMICS_WHITEPAPER_v2.md)

---

## Performance (Projected)

~1 GOPS @ ~50 MHz @ ~1W ternary per die (projected, pending tape-out 2026-12-16)

---

## Cross-Links

- Canonical hardware catalog: [gHashTag/NeuronConstant](https://github.com/gHashTag/NeuronConstant)
- Sibling die -- Euler (reasoning organ): [gHashTag/tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler)
- Sibling die -- Gamma (neocortex organ): [gHashTag/tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma)
- One-Computer paradigm: [UNIFIED_COMPUTER_PARADIGM.md](https://github.com/gHashTag/NeuronConstant/blob/main/docs/architecture/UNIFIED_COMPUTER_PARADIGM.md)
- Tokenomics whitepaper v2: [TRI_TOKENOMICS_WHITEPAPER_v2.md](https://github.com/gHashTag/NeuronConstant/blob/main/docs/tokenomics/v2/TRI_TOKENOMICS_WHITEPAPER_v2.md)

---

## Contributing

Pull requests are welcome. For RTL changes, open an issue first. This repo is a Tiny Tapeout submission mirror -- substantive RTL lives in [gHashTag/NeuronConstant](https://github.com/gHashTag/NeuronConstant) under `tiles/phi-anchor/`.

---

## License

Apache-2.0 -- see [LICENSE](LICENSE)

**Author:** Dmitrii Vasilev | **Email:** admin@t27.ai | **Site:** t27.ai
**DOI:** [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
