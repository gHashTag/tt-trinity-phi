# ARCHITECTURE QUICK WINS — tt-trinity-phi (φ-anchor)

> **Posture:** **PLAN / SCOPING DOC.** This document proposes high
> impact-to-effort improvements for the φ-anchor chip, grounded in what
> actually exists in this repo today and informed by the TRI-NET
> competitive-architecture research report. Every quick win names the
> exact files it would touch, the claims-matrix row it would create or
> update, and the R5-honest tier of any new claim. No quick win below
> changes RTL semantics or adds a measured-silicon claim.

Last updated: 2026-05-18.

Cross-refs: [`VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md) ·
[`TRIPLE_DECKER_STATE_MACHINE.md`](TRIPLE_DECKER_STATE_MACHINE.md) ·
[`../TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) ·
[`../GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) ·
[`../TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) ·
[`../D2D_PROTOCOL.md`](../D2D_PROTOCOL.md).

---

## 0. What's actually on this chip today (audit summary)

φ-anchor is the 1×1 reference SKU. Reading `src/` (48 `.v` files) and
`info.yaml`:

| Subsystem | Files | Rung today |
|---|---|---|
| Canonical GF16 dot4 anchor                  | `src/gf16_dot4.v`, `src/gf16_add.v`, `src/gf16_mul.v` (legacy XOR), `src/trinity_gf16_tile.v`, `src/tt_um_trinity_nano.v` | **GDS / TAPEOUT** |
| Lucas POST (`φ² + φ⁻² = 3`)                 | `src/phi_anchor_post.v`, `src/lucas_rom.v`, `src/sacred_constants_rom.v`, `src/crown47_rom*.v` | **SYNTH** |
| Provenance / safety                          | `src/hwrng_lfsr.v`, `src/restraint_ctrl.v`, `src/trinity_friend_foe.v` | **SYNTH** |
| GF{4,8,12,16,20,24,32,64,128,256} adders     | `src/gf{4,8,12,16,20,24,32,64,128,256}_add.v`, `src/gf_formats.v` | **RTL** (compiled, not exercised individually in `test/tb.v`) |
| Quantizers                                   | `src/{int4,int8,nf4,fp8_e4m3,fp8_e5m2,posit16}_quantizer.v`, `src/gf16_to_fp16.v`, `src/gf16_to_posit16.v` | **RTL** |
| Power modules                                | `src/avs_controller_96.v` (AVS, not CAP_BOOST), `src/fbb_active_path.v`, `src/dfs_gate.v`, `src/purkinje_thermal_gate.v`, `src/drowsy_ret.v`, `src/subth_clk.v` | **RTL/SYNTH** |
| Sparse / sacred opcodes                      | `src/{sparse_mask,sparse_skip,null_pe,spec_exit,stoch_round,holo_mux_x4,lut_npu_81_entry,lane_l_precheck,tri_mant_mul}.v` | **RTL** |

What's **missing** vs. the line-level marketing:

- **No RBB RTL.** `VC-DECK-2` in the matrix is `NOT MEASURED`.
- **No CAP_BOOST RTL** — AVS-96 is not CAP_BOOST. `VC-DECK-3`.
- **No host bridge / D2D harness.** The D2D protocol is a frozen
  spec but there's no in-repo bridge that drives it; SYNC_STROBE / ACK
  paths are only exercised by `test/tb.v` indirectly.
- **No NMSE harness.** Golden vectors landed in
  [`docs/vectors/nmse/`](vectors/nmse/) but nothing emits a per-run
  report under `bench/nmse/<git_sha>.json` yet.
- **No body-bias operating-point table.** `TOPS_W_22FDX_PROJECTION.md`
  quotes a 28–120 TOPS/W band but does not enumerate `(V, Vbb, freq,
  power)` rows.

These five gaps are the quick wins below.

---

## Quick Wins (φ-anchor, ranked by impact / effort)

### QW-Phi-1 · Body-bias operating-point table

**Status today:** missing. The 22FDX band (`VC-22FDX-1`) is one number;
the assumption set is documented in
[`../TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §3 but
not broken down by operating point.

**Add a per-deck operating-point table** in
[`../TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §2.5
(new sub-section), one row per `(deck_state, V, Vbb, freq_target,
active_power_target, leakage_target)`:

| Deck state | V (V) | Vbb (V) | Freq target | Active power | Leakage |
|---|---|---|---|---|---|
| IDLE       | 0.50 | 0.0   | parked  | (PROJECTED) | (PROJECTED) |
| RBB        | 0.50 | −1.5  | parked  | (PROJECTED, low) | (PROJECTED, very low) |
| FBB        | 0.50 | +1.5  | high    | (PROJECTED) | (PROJECTED) |
| CAP_BOOST  | 0.55 (boosted) | +1.5 | peak | (PROJECTED, burst) | n/a |

Cite GF's published 22FDX body-bias range as the methodology source
(±1.5 V — already in the report). New matrix row: `VC-22FDX-4`.

**Tier:** ◷ PROJECTED. **Effort:** ~1 hour. **Risk:** none — table
extends the existing projection.

**Why it matters:** competitors publish per-PVT operating points
(Tenstorrent Blackhole's 1.35 GHz / 300 W rows are the gold standard).
Without per-state rows, the 22FDX band reads like marketing.

---

### QW-Phi-2 · GF16 NMSE harness emitting `bench/nmse/<git_sha>.json`

**Status today:** the golden vector
[`vectors/nmse/gf16_vs_bfloat16.golden.json`](vectors/nmse/gf16_vs_bfloat16.golden.json)
is the contract; no harness emits per-run reports against it.

**Land a Python script** `bench/nmse/run.py` that:

1. Reads the golden vector to learn `(N, seed, distributions, formats,
   tolerances)`.
2. Generates samples (PCG64 seeded as documented in the vector's
   `rng.seed_uint64`).
3. Runs the documented quantise/dequantise paths for GF16 (mirror of
   `specs/numeric/gf16.t27` decoded in software) and bfloat16.
4. Emits the report at `bench/nmse/<git_sha>.json` with the same
   schema plus `actual.nmse_db` per `(dist, format)`.
5. Compares against `expected.nmse_db ± expected.tolerance_db` and
   exits non-zero on a fail.

Wire it into the spec gate as an optional step (skipped if numpy is
absent) — same pattern as the `t27c` check.

New matrix row: `VC-NMSE-5` ("harness emits per-run report against
golden vector"). Tier flips from ▢ SPEC to ⊙ PRE-SILICON on the
distributions where the host harness has run.

**Tier:** ⊙ PRE-SILICON (simulation only — no silicon NMSE). **Effort:**
~1 day. **Risk:** low; the script is hermetic.

**Why it matters:** competitor research (`MXFP8 + bf16 activations`)
sets the bar for "GF16 vs bfloat16" claims. A repo with the *contract*
but no *harness* still gets dismissed as a SPEC stub.

---

### QW-Phi-3 · Per-format `test/tb_v1.v` coverage

**Status today:** `info.yaml` lists 48 source files; `test/tb.v` only
exercises the canonical anchor and Lucas POST. `STATUS.md` SYNTH-1
explicitly calls this out. GF{8,20,24,32,64,128,256} adders, the eight
quantizers, AVS-96, and the FBB path are compiled into the GDS but
never functionally exercised.

**Add per-format cocotb cases** under `test/test_v1.py`:

- For each `gfN_add.v`: drive a small fixed table of inputs and read
  back via the existing `trinity_packet.vh` path (or expose a debug
  mux on `uio_out`).
- For each quantizer: feed a fixed input vector and check the round
  trip against a software reference.
- For `fbb_active_path.v` and `purkinje_thermal_gate.v`: assert the
  enable/disable transitions match the Triple-Decker state-machine
  spec (`VC-DECK-4`).

This is the SYNTH-1 checklist item in `STATUS.md` — it moves several
modules from "compiled" to "PRE-SILICON simulation" (⊙). New matrix
rows: `VC-GF-5..N` per format.

**Tier:** ⊙ PRE-SILICON. **Effort:** 2–3 days (mostly per-module
boilerplate). **Risk:** low; the test harness is established.

**Why it matters:** every module in `info.yaml` that's compiled but
unexercised is a footgun in the claims surface — a reviewer can
correctly say "that's a `*.v` file, not a verified feature".

---

### QW-Phi-4 · Friend/foe + restraint state-machine spec doc

**Status today:** `src/restraint_ctrl.v` (CLARA Gap-4) and
`src/trinity_friend_foe.v` exist and are at SYNTH, but there is no
state-machine doc analogous to
[`TRIPLE_DECKER_STATE_MACHINE.md`](TRIPLE_DECKER_STATE_MACHINE.md).

**Add `docs/RESTRAINT_FF_STATE_MACHINE.md`** with:

- States: `BOOT → POST_GATE → FF_CHALLENGE → FF_RESPONSE → LOAD_PHASE
  → RUN → RESTRAINT_HOLD → ...`.
- Guards: POST pass, FF nonce match, `restraint_mode` input.
- The exact `ui_in[5] = restraint_mode` and
  `MY_ANCHOR = 0xCF` / `PHI_ID = 0x47` constants from RTL.
- Map states 1:1 onto the MLCommons inference power phases (load /
  run / drain / idle) — this is the cross-walk that makes any future
  power claim apples-to-apples comparable to MLPerf submissions.

New matrix row: `VC-FF-1` (state-machine contract). Updates
`VC-D2D-5` evidence link.

**Tier:** ▢ SPEC. **Effort:** ~half a day. **Risk:** none.

**Why it matters:** the report's QW-5 (MLCommons phase mapping) is the
single biggest unlock for "TOPS/W" claims becoming trustworthy. Doing
it once on phi sets the template for euler/gamma.

---

### QW-Phi-5 · MX-format positioning note for GF16

**Status today:** [`../GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md)
defines the protocol but does not position GF16 against the MX Alliance
(MXFP4/6/8, MXINT8) — the dominant block-FP standard in 2026.

**Add a "GF16 vs MX" sub-section** to
[`../GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) (or a new
`docs/GF16_VS_MX.md`) that states:

- GF16 is a **per-tensor** 16-bit floating-point format, not a
  block-FP shared-exponent format like MX.
- The closest MX cousin is **MXFP8 E4M3** (per-32-element shared
  exponent + 8-bit elements); GF16 trades the block-share for a wider
  per-element exponent (E6 vs E4) and a longer mantissa (M9 vs M3).
- Where GF16 wins: per-tensor dynamic range (D-5 powers-of-two
  distribution in the golden vector).
- Where MX wins: storage per element (8 bits vs 16) and bandwidth into
  the MAC.
- GF16's role is **on-die compute precision**, complementing rather
  than replacing block-FP transport.

Cite the MX Alliance arXiv paper (already in the research report).
New matrix row: `VC-GF-6` ("GF16 / MX positioning").

**Tier:** ◷ PROJECTED (analytical). **Effort:** ~half a day. **Risk:**
none — narrative only.

**Why it matters:** GF16 sounds proprietary unless explicitly anchored
to the published numerical-format ecosystem. The report's QW-3.

---

### QW-Phi-6 · UCIe-style D2D headline numbers

**Status today:** D2D conformance vectors land in `conformance/d2d/`;
[`../D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) describes roles but not
headline numbers.

**Add a UCIe-parallel summary** to
[`../D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §1 with:

| Layer | TRI-NET D2D | UCIe Standard Package | Notes |
|---|---|---|---|
| Physical    | 3-wire, ≤25 MHz sampling, ≤30 cm trace | 16/64-lane PHY at 4–32 GT/s | TRI-NET is bond-trace, not packaged interconnect. |
| Link        | 8-bit CRC-8 (poly 0x07), 3-retry → RESYNC | 16-bit CRC, Flit retry | Same shape; smaller numbers. |
| Protocol    | TYPE bytes `{0x47, 0x93, 0xE0, 0xC1}` | Streaming / message | TRI-NET protocol is fixed-type. |
| Power       | (PROJECTED, fJ/bit not yet quoted)        | ~1 pJ/bit              | Plan: derive from `gf16_dot4` energy estimate. |
| Conformance | `conformance/d2d/*.json` (5 vectors)      | UCIe compliance suite  | Schema documented; runnable. |

New matrix row: `VC-D2D-6` ("UCIe parallel summary"). Tier of the
fJ/bit row: ◷ PROJECTED initially, ⊙ PRE-SILICON once a back-of-envelope
power-monitor patch lands on `src/tt_um_trinity_nano.v`.

**Tier:** ◷ PROJECTED. **Effort:** ~half a day. **Risk:** none.

**Why it matters:** report QW-4. Engineers familiar with UCIe will
otherwise treat TRI-NET D2D as exotic.

---

### QW-Phi-7 · NVDLA-class positioning sentence

**Status today:** [`../COMPETITORS.md`](../COMPETITORS.md) lists peer
chips but not NVDLA, the most-cited open-source inference accelerator.

**Add one paragraph** to [`../COMPETITORS.md`](../COMPETITORS.md) that
explicitly positions φ-anchor against NVDLA's 7.9 TOPS/W on Jetson AGX
Xavier:

- Same model: open RTL, configurable, synthesisable.
- φ-anchor is much smaller (1×1 vs full NVDLA).
- φ-anchor's pre-silicon target on 22FDX (after FBB application of
  GF's published ~45% power reduction) puts it in NVDLA-class
  efficiency *if and only if* RBB and CAP_BOOST land — see
  `VC-22FDX-2`.

New matrix row: `VC-COMP-1`. **Tier:** ◷ PROJECTED.

**Effort:** ~30 minutes. **Risk:** none.

**Why it matters:** NVDLA is the canonical reference for "configurable
open inference RTL" — not mentioning it leaves a credibility gap.

---

### QW-Phi-8 · `info.yaml` TOPS/W string — annotate, do not change

**Observation:** `info.yaml` contains the string `"TOPS/W: 75 baseline,
405 with AVS-96 (5.4× boost)"` in `project.description`. That line
predates the verification hardening layer; changing it would touch
RTL-adjacent metadata in a way that requires re-running the GDS flow.

**Action:** **do not edit** `info.yaml` in this layer. Instead, add an
explicit row to [`VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md)
that:

- Quotes the existing string.
- Marks it as ◷ PROJECTED.
- Names `VC-NM-1` as the governing anti-claim ("no measured silicon
  TOPS/W").
- Specifies that a future PR may move the string into a footnote with
  the legend mark.

New matrix row: `VC-INFOYAML-1`. **Tier:** ◷ PROJECTED, with a sticky
anti-claim attached.

**Effort:** ~10 minutes. **Risk:** none — does not touch RTL or
synthesis inputs.

**Why it matters:** the string is the most visible single number on
the chip's TT shuttle page; the matrix has to reflect it or the gate's
"every number has a row" rule is a half-truth.

---

## Ranking summary

| Quick win | Tier of new evidence | Effort | Impact |
|---|---|---|---|
| **QW-Phi-1** body-bias operating-point table          | ◷ PROJECTED       | ~1 h    | high (22FDX claim credibility) |
| **QW-Phi-2** NMSE harness `bench/nmse/<sha>.json`     | ⊙ PRE-SILICON     | ~1 d    | very high (flips ▢ SPEC → ⊙) |
| **QW-Phi-3** per-format cocotb coverage               | ⊙ PRE-SILICON     | 2–3 d   | high (moves 20+ modules to ⊙) |
| **QW-Phi-4** restraint/FF state-machine doc           | ▢ SPEC            | ~0.5 d  | high (MLCommons mapping) |
| **QW-Phi-5** GF16 / MX positioning                    | ◷ PROJECTED       | ~0.5 d  | high (ecosystem anchoring) |
| **QW-Phi-6** UCIe-parallel D2D summary                | ◷ PROJECTED       | ~0.5 d  | medium-high (integrator appeal) |
| **QW-Phi-7** NVDLA-class positioning                  | ◷ PROJECTED       | ~0.5 h  | medium (credibility) |
| **QW-Phi-8** `info.yaml` TOPS/W string annotation     | ◷ PROJECTED + ✗   | ~10 min | medium (matrix completeness) |

Priorities **1, 4, 7, 8** are all <1 day and unblock the next bigger
wins; they are the suggested next PR after this one.

---

## What these quick wins explicitly do NOT do

- They do **not** add new RTL semantics, change pin assignments, or
  modify `info.yaml`'s source-files list.
- They do **not** mint a new Zenodo DOI; deposition timing follows
  [`RELEASE_MANIFEST_TRINET_V1.md`](RELEASE_MANIFEST_TRINET_V1.md).
- They do **not** promote any row to MEASURED-silicon. Every new
  evidence row lands at ⊙ PRE-SILICON, ◷ PROJECTED, or ▢ SPEC.
- They do **not** claim TOPS/W as a point estimate. The 22FDX band
  stays a band (`VC-22FDX-1`).
- They do **not** require any change to the existing `gds.yaml` /
  `test.yaml` / `tri-test.yml` / `fpga.yaml` workflows.

---

## Cross-references

- [`VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md) — every quick win names a `VC-*` row it would add or update.
- [`TRIPLE_DECKER_STATE_MACHINE.md`](TRIPLE_DECKER_STATE_MACHINE.md) — referenced by QW-Phi-3 / QW-Phi-4.
- [`../GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) — protocol that QW-Phi-2 implements.
- [`../TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) — QW-Phi-1 extends §2.5.
- [`../D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) — QW-Phi-6 extends §1.
- [`../COMPETITORS.md`](../COMPETITORS.md) — QW-Phi-7 adds the NVDLA paragraph.
- [`../STATUS.md`](../STATUS.md) — checklist items SYNTH-1 / SPEC-NMSE-1 / SPEC-DECK-1 align with QW-Phi-3 / QW-Phi-2 / QW-Phi-1.
- TRI-NET competitive-architecture report (external) — provides QW-1..QW-10 framing this doc consumes.
