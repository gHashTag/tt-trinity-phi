# CLARA_TRACEABILITY — tt-trinity-phi (φ-anchor)

> Map between DARPA-style assurance themes and the **evidence committed in
> this repository**. The φ-anchor only claims a small subset of the full
> ten-gap CLARA story — see [`docs/CLARA_PROOF_MANIFEST.md`](docs/CLARA_PROOF_MANIFEST.md)
> for the proof-manifest view and [`docs/TRI_NET_DARPA_CLARA_PROPOSAL.md`](docs/TRI_NET_DARPA_CLARA_PROPOSAL.md)
> for the full line-level proposal.

Reference: DARPA CLARA programme overview — <https://www.darpa.mil/research/programs/clara>.

This file is conservative: only assurance themes that have a concrete
file-level anchor in this repo are claimed as "in-scope". The other themes
are flagged as out-of-scope-for-this-chip and routed to the sibling repos.

---

## Scope on this chip

The φ-anchor is the **proof-seed / identity** chip of TRI-NET. Its assurance
surface is intentionally small. Three themes are in-scope here; the heavier
themes live in `tt-trinity-euler` and `tt-trinity-gamma`.

| Theme | In scope for φ-anchor? | Why |
|---|---|---|
| **Identity / provenance** (deterministic anchor + die-unique nonce) | ✅ Yes | Smallest die, primary "is this really a TRI-NET part?" check. |
| **Bounded rationality** (CLARA Gap-4 style) | ✅ Yes (minimal) | Reference implementation lives here. |
| **Proof seed** (Lucas identity φ²+φ⁻²=3) | ✅ Yes | Anchor proof for the whole line. |
| Full ternary ALU / Kleene K3 logic | ❌ Off-chip (euler / gamma) | No K3 ALU in this repo. |
| Adversarial input filter / red-team | ❌ Off-chip (euler / gamma) | No `redteam_filter` instantiated in this repo. |
| Explainability unit (proof-trace MAC) | ❌ Off-chip (euler / gamma) | Not present in φ-anchor RTL. |
| Holographic / D2D mesh assurance | ❌ Off-chip (gamma) | φ-anchor is single tile. |

---

## Evidence table — what proves what, where

| Assurance claim | Evidence file in this repo | Notes |
|---|---|---|
| **Canonical cross-die anchor** — `dot4(1.0, 2.0, 3.0, 4.0) = 0x47C0` in GF16 | [`src/gf16_dot4.v`](src/gf16_dot4.v) (combinational implementation), [`test/tb.v`](test/tb.v) (testbench), [`.github/workflows/test.yaml`](.github/workflows/test.yaml) (CI gate) | Same constant must appear on `{uio_out, uo_out}` for all three TRI-NET dies at reset. |
| **Lucas POST chain** (L₂=3, L₃=4, L₄=7, L₅=11, L₆=18, L₇=29) → proves φ²+φ⁻²=3 by Binet | [`src/phi_anchor_post.v`](src/phi_anchor_post.v), [`src/lucas_rom.v`](src/lucas_rom.v) | Failure latches `phi_ok=0` sticky-low; status visible via POST status byte. |
| **Bounded rationality (Gap-4 sketch)** — bound output to `K_UNKNOWN` when restraint mode is asserted | [`src/restraint_ctrl.v`](src/restraint_ctrl.v) | RTL gate; the corresponding Coq theorem lives in the external [`trinity-clara`](https://github.com/gHashTag/trinity-clara) repo, not in this one. |
| **Die-unique provenance nonce** | [`src/hwrng_lfsr.v`](src/hwrng_lfsr.v) | 16-bit LFSR seeded from POR state — die-unique up to seed reproducibility. |
| **Friend / foe (TRN handshake)** — chip identifies itself as `MY_ANCHOR=φ` to mesh peers | [`src/trinity_friend_foe.v`](src/trinity_friend_foe.v) | Used by gamma / euler to validate cross-die identity. |
| **R-SI-1 (no new `*` operators)** — silicon-level rule eliminating multiplier switching energy and matching the ternary-substrate story | [`.github/workflows/no_star.yaml`](.github/workflows/no_star.yaml) + cross-check in [`.github/workflows/test.yaml`](.github/workflows/test.yaml) (Yosys `$mul` audit) | Legacy `gf16_mul.v` is grandfathered (XOR-based GF16 multiply, no `*` operator in synthesisable form). |
| **Synthesis + lint gate** — Yosys synth and Verilator `-Wall` lint must pass | [`.github/workflows/fpga.yaml`](.github/workflows/fpga.yaml) | Resource report uploaded as artifact. |
| **Tape-out path** — OpenLane2 → SKY130A → `tt_submission` | [`.github/workflows/gds.yaml`](.github/workflows/gds.yaml), [`.github/workflows/sky130-nightly.yml`](.github/workflows/sky130-nightly.yml) | Uses `TinyTapeout/tt-gds-action@ttsky26b`, runs TT precheck + GL test + viewer. |
| **Cross-die consistency** | [`.github/workflows/tri-test.yml`](.github/workflows/tri-test.yml) | Per-repo check that the canonical anchor and R-SI-1 status agree across the line. |
| **Numeric format registry** — `.t27` specs imported from the toolchain | [`specs/numeric/`](specs/numeric/) | Single source of truth for GF4..GF256, FP8 E4M3/E5M2, NF4, Posit16, int4/int8, binary16. |
| **Conformance vector** | [`conformance/FORMAT-SPEC-001.json`](conformance/FORMAT-SPEC-001.json) | Used by the t27 cross-die tests. |

Anything **not** in this table is **not** claimed by this repo. If a future
audit asks "where is the proof?", the answer must point to a row above.

---

## CLARA / DARPA references

Restrained, evidence-backed only:

- DARPA CLARA programme page — <https://www.darpa.mil/research/programs/clara> (programme exists; this repo *aligns* with it, it is not a DARPA contractee).
- BitNet b1.58 (motivates ternary substrate) — <https://arxiv.org/abs/2402.17764>.
- Tiny Tapeout shuttle catalogue — <https://tinytapeout.com/chips/>.

---

## How to verify yourself

```bash
# 1. Sim the canonical anchor (locally, requires iverilog).
iverilog -I src -o /tmp/tb.out src/*.v test/tb.v && vvp /tmp/tb.out

# 2. R-SI-1 audit (locally, plain grep — same logic as the workflow).
grep -nE '\*' src/*.v | grep -v gf16_mul.v | grep -v '//' || echo "R-SI-1 PASS"

# 3. Inspect Lucas POST module.
sed -n '1,80p' src/phi_anchor_post.v
sed -n '1,40p' src/lucas_rom.v

# 4. Inspect restraint controller (Gap-4 sketch).
sed -n '1,80p' src/restraint_ctrl.v
```

Every workflow file referenced above is in [`.github/workflows/`](.github/workflows/);
inspect them directly to see what is actually run on CI.

---

## What this document is NOT

- **Not a DARPA CLARA award notice.** No contractual relationship is claimed.
- **Not a formal proof.** Coq proofs live in the [`coq/`](coq/) /
  [`trios-coq/`](trios-coq/) trees in this repo and in the external
  [`trinity-clara`](https://github.com/gHashTag/trinity-clara) repo. Their
  current status (proven / admitted) is whatever is committed there — this
  file does not restate it.
- **Not a silicon claim.** See [`STATUS.md`](STATUS.md) for what has reached
  SILICON rung vs what has not.
