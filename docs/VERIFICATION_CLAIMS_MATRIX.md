# VERIFICATION CLAIMS MATRIX — tt-trinity-phi (φ-anchor)

> **Purpose.** Single, machine-checkable index of every **numerical
> claim** that appears in the TRI-NET φ-anchor docs and specs. Each row
> names *what* is claimed, *where* it lives, *how* it can be verified
> (or that it currently can't be), and the **anti-claim** — the
> measurement or condition that would falsify it.
>
> This file is normative: a numerical claim that lands in any other doc
> in this repo MUST also appear here. The spec CI gate
> [`scripts/check_trinet_specs.sh`](../scripts/check_trinet_specs.sh)
> enforces it.

Last updated: 2026-05-18.

---

## R5 honesty posture

Every row honours the R5 posture documented in
[`BENCHMARKS.md`](../BENCHMARKS.md):

- No silicon TOPS / TOPS-per-watt is claimed as measured.
- No measured NMSE is claimed (the harness is a SPEC; vectors are
  *golden* reference vectors, not silicon captures).
- No DOI / funding / fabrication line is asserted that does not
  already exist in the repo's Zenodo bundle or CHANGELOG.
- A row whose status is **PROJECTED** is reproducible from RTL intent
  or from the t27 format registry — not from a die.
- A row whose status is **MEASURED** is reproducible from a CI
  workflow that ships in this repo.

---

## Column legend

| Column | Meaning |
|---|---|
| **Claim ID**          | Stable identifier (`VC-<area>-<n>`). Other docs cite this. |
| **Claim**             | One-line statement of the numerical fact. |
| **Location**          | Repo-relative path(s) where the claim appears. |
| **Evidence / Witness**| RTL file, t27 spec, JSON vector, or report that backs it. |
| **Harness**           | Script / workflow / test that exercises the evidence. `n/a` if there is no executable witness yet. |
| **Status**            | `MEASURED` (CI), `PROJECTED` (architecture), `SPEC` (planned harness), `NOT MEASURED` (explicitly out of scope). |
| **Anti-claim**        | What would falsify the row. Used by reviewers and by the spec CI gate. |

---

## A. Canonical anchor (0x47C0 / cross-die)

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-ANCHOR-1  | `dot4(1.0, 2.0, 3.0, 4.0)` in GF16(2⁴) on `{uio_out[7:0], uo_out[7:0]}` after reset, `load_mode=0`, equals `0x47C0`. | [`BENCHMARKS.md`](../BENCHMARKS.md) M-1, [`STATUS.md`](../STATUS.md), [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §2 | [`src/gf16_dot4.v`](../src/gf16_dot4.v), [`test/tb.v`](../test/tb.v) | [`.github/workflows/test.yaml`](../.github/workflows/test.yaml) job *IVerilog canonical anchor test* | MEASURED | The CI job emits a value ≠ `0x47C0` on the documented pin set after reset with `load_mode=0`. |
| VC-ANCHOR-2  | `uio_oe == 0xFF` after reset (all `uio` lines driven). | [`BENCHMARKS.md`](../BENCHMARKS.md) M-2 | [`src/gf16_dot4.v`](../src/gf16_dot4.v) | [`.github/workflows/test.yaml`](../.github/workflows/test.yaml) | MEASURED | `uio_oe` bit clears in SIM. |
| VC-ANCHOR-3  | TRI-NET cross-die anchor parity: every die in the line must reproduce `0x47C0` before initiating compute. | [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §2, [`.github/workflows/tri-test.yml`](../.github/workflows/tri-test.yml) | [`src/gf16_dot4.v`](../src/gf16_dot4.v), [`info.yaml`](../info.yaml) | [`.github/workflows/tri-test.yml`](../.github/workflows/tri-test.yml) | MEASURED | tri-test workflow fails on any die's anchor mismatch. |
| VC-ANCHOR-4  | Anchor latency is **1 cycle combinational** at the TT clock rate (RTL-level only). | [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §2 | [`src/gf16_dot4.v`](../src/gf16_dot4.v) | iverilog timing trace in [`test/tb.v`](../test/tb.v) | PROJECTED | Synth-level STA report shows >1 cycle through the GF16 dot4 combinational cone. |

## B. Lucas POST / proof anchor

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-LUCAS-1  | The Lucas sequence L₂..L₇ on φ-anchor is `{3, 4, 7, 11, 18, 29}` and proves `φ² + φ⁻² = 3` via Binet. | [`BENCHMARKS.md`](../BENCHMARKS.md) M-9, [`STATUS.md`](../STATUS.md) | [`src/phi_anchor_post.v`](../src/phi_anchor_post.v), [`src/lucas_rom.v`](../src/lucas_rom.v) | [`test/tb.v`](../test/tb.v) `tb_post` recipe | MEASURED | Any of L₂..L₇ deviates from the listed integers in SIM. |
| VC-LUCAS-2  | `phi^2 = phi + 1` is exact in IEEE binary64 with residual `0.0` and tolerance `1e-15`. | [`conformance/FORMAT-SPEC-001.json`](../conformance/FORMAT-SPEC-001.json) `phi_identity` | `conformance/FORMAT-SPEC-001.json`, `Kernel/Phi.v` (external Coq ref) | conformance JSON parse | SPEC | The conformance JSON's `residual_f64` is non-zero or exceeds `tolerance`. |

## C. GoldenFloat numeric family

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-GF-1   | GF16 layout: `S=1, E=6, M=9, bias=31`. | [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) §1, [`conformance/FORMAT-SPEC-001.json`](../conformance/FORMAT-SPEC-001.json) | [`specs/numeric/gf16.t27`](../specs/numeric/gf16.t27), [`specs/numeric/formats.t27`](../specs/numeric/formats.t27) | t27c parse (optional), conformance JSON load | SPEC | t27 spec disagrees with the conformance JSON on any of `{S, E, M, bias}` for GF16. |
| VC-GF-2   | bfloat16 layout: `S=1, E=8, M=7, bias=127` (IEEE-non-compliant by definition). | [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) §1, [`conformance/FORMAT-SPEC-001.json`](../conformance/FORMAT-SPEC-001.json) | [`specs/numeric/formats.t27`](../specs/numeric/formats.t27) | conformance JSON load | SPEC | Layout differs from the IEEE-non-compliant bf16 reference. |
| VC-GF-3   | GoldenFloat family covers `{GF4, GF8, GF12, GF16, GF20, GF24, GF32, GF64, GF128, GF256}` with `phi_dist` reported per format. | [`conformance/FORMAT-SPEC-001.json`](../conformance/FORMAT-SPEC-001.json), [`docs/TRI_NET_FORMATS_SUMMARY.md`](../docs/TRI_NET_FORMATS_SUMMARY.md) | [`specs/numeric/*.t27`](../specs/numeric/) | conformance JSON load | SPEC | Any GF<N> in the registry is missing a `.t27` file or its `{bits, sign, exp, mant, bias}` disagrees with the JSON. |
| VC-GF-4   | GF16 is the *primary* GoldenFloat width on φ-anchor. | [`conformance/FORMAT-SPEC-001.json`](../conformance/FORMAT-SPEC-001.json) (`"primary": true`) | [`src/gf16_dot4.v`](../src/gf16_dot4.v), [`src/gf16_add.v`](../src/gf16_add.v), [`src/gf16_mul.v`](../src/gf16_mul.v) | iverilog compile of `src/*.v` | MEASURED | No `gf16_*` module compiles from `src/`. |

## D. NMSE protocol (golden vectors)

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-NMSE-1 | NMSE is reported in dB as `10·log10(Σ(xᵢ-x̂ᵢ)² / Σ xᵢ²)` over a single aggregation, no per-bin tricks. | [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) §2 | [`docs/vectors/nmse/gf16_vs_bfloat16.golden.json`](vectors/nmse/gf16_vs_bfloat16.golden.json) | [`scripts/check_trinet_specs.sh`](../scripts/check_trinet_specs.sh) (presence check) | SPEC | A report under `bench/nmse/` uses a different aggregation rule. |
| VC-NMSE-2 | Reference distributions are exactly `D-1..D-6` with `N = 1,048,576` samples per distribution and seed `0x47C0`. | [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) §3 | [`docs/vectors/nmse/gf16_vs_bfloat16.golden.json`](vectors/nmse/gf16_vs_bfloat16.golden.json) | `scripts/check_trinet_specs.sh` parses the JSON's `sample_count` and `seed` | SPEC | A report uses a different `N`, seed, or a non-listed distribution and is still considered protocol-conformant. |
| VC-NMSE-3 | The φ-anchor harness operates in `RTL_ONLY` or `SILICON` mode; today's runs are `RTL_ONLY` and no silicon NMSE is claimed anywhere. | [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) §4, §7 | repo-wide grep | grep audit in `scripts/check_trinet_specs.sh` | NOT MEASURED | Any doc outside this matrix asserts a `SILICON`-mode NMSE number. |
| VC-NMSE-4 | The golden vectors are reference *baselines* with explicit tolerances; they are **not** silicon captures. | [`docs/vectors/nmse/README.md`](vectors/nmse/README.md) | [`docs/vectors/nmse/gf16_vs_bfloat16.golden.json`](vectors/nmse/gf16_vs_bfloat16.golden.json) | `scripts/check_trinet_specs.sh` JSON load | SPEC | The vector file's `provenance.mode` is set to `SILICON`. |

## E. D2D / interconnect protocol

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-D2D-1  | Wire-level D2D uses a **3-wire** interface: `LOAD_MODE`, `SYNC_STROBE`, open-drain `ACK` (wired-AND across slaves). | [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §1, [`docs/INTERCONNECT_PROTOCOL_V1.md`](../docs/INTERCONNECT_PROTOCOL_V1.md) §4 | [`docs/INTERCONNECT_PROTOCOL_V1.md`](../docs/INTERCONNECT_PROTOCOL_V1.md) | n/a (board-level) | PROJECTED | The interconnect spec changes wire count or topology. |
| VC-D2D-2  | φ-anchor occupies the **master** position in the v1.0 interconnect state machine. | [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §2 | [`src/restraint_ctrl.v`](../src/restraint_ctrl.v), [`docs/INTERCONNECT_PROTOCOL_V1.md`](../docs/INTERCONNECT_PROTOCOL_V1.md) | n/a (board-level) | PROJECTED | A future protocol revision moves the master role off φ-anchor without bumping the protocol version. |
| VC-D2D-3  | Conformance vectors cover: valid header, bad CRC, unsupported opcode, timeout/retry, and multi-chip ordering. | [`conformance/d2d/*.json`](../conformance/d2d/) | JSON vectors in `conformance/d2d/` | `scripts/check_trinet_specs.sh` (presence + JSON parse) | SPEC | A required vector is missing or fails JSON parse. |
| VC-D2D-4  | Today's fabric scales to at most **2 slaves** (wired-AND ACK across 2). N>2 needs a new arbitration scheme. | [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §4.1 | [`docs/INTERCONNECT_PROTOCOL_V1.md`](../docs/INTERCONNECT_PROTOCOL_V1.md) §4 | n/a | PROJECTED | The interconnect spec is updated for N>2 without revisiting wire C. |
| VC-D2D-5  | Friend/foe handshake on φ-anchor uses `MY_ANCHOR = 0xCF`. | [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §3 | [`src/trinity_friend_foe.v`](../src/trinity_friend_foe.v) | iverilog compile + cocotb | MEASURED | The constant in RTL differs from `0xCF`. |

## F. Triple-Decker (RBB / FBB / CAP_BOOST)

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-DECK-1 | **FBB** (Forward Body Bias) is at **SYNTH** rung on φ-anchor today. Sacred opcode is `0xF2`. | [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3 | [`src/fbb_active_path.v`](../src/fbb_active_path.v), [`specs/fpga/fbb_active_path.t27`](../specs/fpga/fbb_active_path.t27) | [`.github/workflows/fpga.yaml`](../.github/workflows/fpga.yaml) | MEASURED | `fbb_active_path.v` missing from `src/` or opcode in RTL differs from `0xF2`. |
| VC-DECK-2 | **RBB** (Reverse Body Bias) is **not implemented** on φ-anchor (planned only). | [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3, §4.1 | absence of `src/rbb_*.v` | grep audit in `scripts/check_trinet_specs.sh` | NOT MEASURED | A `src/rbb_*.v` file lands without a matching SPEC update. |
| VC-DECK-3 | **CAP_BOOST** is **not implemented** on φ-anchor (planned only); AVS-96 is *not* CAP_BOOST. | [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3, §4.2 | absence of `src/cap_boost*.v`; [`src/avs_controller_96.v`](../src/avs_controller_96.v) covers AVS only | grep audit | NOT MEASURED | A `src/cap_boost*.v` file lands without a matching SPEC update. |
| VC-DECK-4 | The Triple-Deck state machine progression is `IDLE → RBB → FBB → CAP_BOOST → IDLE` with guards, cooldown, and brownout/overcurrent fallback. | [`docs/TRIPLE_DECKER_STATE_MACHINE.md`](TRIPLE_DECKER_STATE_MACHINE.md) | spec doc | doc presence check in `scripts/check_trinet_specs.sh` | SPEC | The state-machine spec lacks one of the required transitions or fallbacks. |

## G. 22FDX projection (architecture, not silicon)

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-22FDX-1 | Projected TOPS/W on 22FDX (ternary) lies in the **28–120 TOPS/W band**; this is a band, never a point estimate. | [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §2, [`README.md`](../README.md) Green-AI, [`BENCHMARKS.md`](../BENCHMARKS.md) | architectural derivation from RTL intent | n/a (notebook planned under `bench/22fdx/`) | PROJECTED | Any doc quotes a single TOPS/W point estimate, or applies the band to SKY130A. |
| VC-22FDX-2 | The projection assumes a **full Triple-Deck deployment** (RBB + FBB + CAP_BOOST); φ-anchor today implements only FBB. | [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §3 | [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) | n/a | PROJECTED | The assumption is dropped from the 22FDX doc without revising the band. |
| VC-22FDX-3 | FD-SOI back-bias range used in the projection is **±1.5 V**. | [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §1 | architectural assumption | n/a | PROJECTED | A different back-bias range is asserted without updating the projection. |

## H. Cell-count snapshots (architecture, not post-synth)

| Claim ID | Claim | Location | Evidence / Witness | Harness | Status | Anti-claim |
|---|---|---|---|---|---|---|
| VC-CELL-1 | `gf16_dot4` ≈ 50 cells (RTL intent). | [`BENCHMARKS.md`](../BENCHMARKS.md) cell-count snapshot | [`src/gf16_dot4.v`](../src/gf16_dot4.v) | `fpga.yaml` resource report | PROJECTED | Resource report shows a materially different module-level count; doc not updated. |
| VC-CELL-2 | Core (pre-v1.0.0) totals ≈ **850 cells @ 60% density**. | [`BENCHMARKS.md`](../BENCHMARKS.md) | sum of per-module estimates | `fpga.yaml` resource report | PROJECTED | Resource report contradicts the total without a doc update. |

## I. Explicit non-claims (NOT MEASURED)

These rows exist to *prevent* claims, not to make them. Any doc that
contradicts a row in this section MUST be flagged by the spec gate.

| Claim ID | Anti-claim being preserved | Location |
|---|---|---|
| VC-NM-1 | No measured silicon TOPS / TOPS-per-watt is claimed. | [`BENCHMARKS.md`](../BENCHMARKS.md) §"What is NOT measured" N-1 |
| VC-NM-2 | No measured energy-per-op. | `BENCHMARKS.md` N-2 |
| VC-NM-3 | No measured silicon NMSE. | `GF16_BFLOAT16_NMSE.md` §7 |
| VC-NM-4 | No yield / DPM. | `BENCHMARKS.md` N-5 |
| VC-NM-5 | No physical-die WNS / slack (OpenLane STA ≠ silicon). | `BENCHMARKS.md` N-3 |
| VC-NM-6 | No fabricated DOI / funding line beyond the existing Zenodo `10.5281/zenodo.19227877`. | [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §4 |

---

## How to add or change a row

1. Edit this file first. Pick the lowest-free `VC-<area>-<n>` and add the row with all seven columns populated.
2. Cite the new `VC-…` ID from the doc that introduces (or modifies) the numerical claim.
3. If the row's `Harness` is anything other than `n/a`, make sure the harness exists or is in the same PR.
4. Run [`scripts/check_trinet_specs.sh`](../scripts/check_trinet_specs.sh). It is the source of truth for which claims are represented.

A claim that appears in any other doc but **does not** appear here is a
spec bug — either remove the claim or add the row.

---

## Cross-references

- [`BENCHMARKS.md`](../BENCHMARKS.md) — MEASURED / PROJECTED / NOT MEASURED ladder this matrix is anchored to.
- [`STATUS.md`](../STATUS.md) — readiness ladder.
- [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) — D2D anchor / role layer.
- [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) — NMSE protocol the §D rows reference.
- [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) — power-deck status the §F rows reference.
- [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) — projection the §G rows reference.
- [`conformance/FORMAT-SPEC-001.json`](../conformance/FORMAT-SPEC-001.json) — numeric registry the §C rows reference.
- [`docs/vectors/nmse/`](vectors/nmse/) — golden NMSE vectors.
- [`conformance/d2d/`](../conformance/d2d/) — D2D conformance vectors.
- [`docs/TRIPLE_DECKER_STATE_MACHINE.md`](TRIPLE_DECKER_STATE_MACHINE.md) — Triple-Decker state machine spec.
- [`scripts/check_trinet_specs.sh`](../scripts/check_trinet_specs.sh) — spec gate that enforces this matrix.
