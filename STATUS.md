# STATUS — tt-trinity-phi (φ-anchor)

> Conservative readiness snapshot for the φ-anchor reference chip of the
> TRI-NET line. Status is graded **only against evidence present in this
> repository** (RTL, CI workflows, specs). No claim is made about measured
> silicon performance.

Last updated: 2026-05-17 (TTSKY26b shuttle window).

---

## Readiness ladder

Trinity uses a six-rung readiness ladder. A higher rung is claimed only if
the rung below it is satisfied **inside this repo** (or its CI artifacts).

| # | Rung | Meaning |
|---|------|---------|
| 1 | **SPEC**     | Numeric / behavioural spec exists and is versioned. |
| 2 | **RTL**      | Synthesisable Verilog implementing the spec is committed. |
| 3 | **SIM**      | Functional sim (cocotb + iverilog) passes the canonical anchor. |
| 4 | **SYNTH**    | Yosys synth + Verilator lint clean. |
| 5 | **GDS / TAPEOUT** | OpenLane2 (SKY130A) flow produces a `tt_submission` artifact; shuttle submission accepted. |
| 6 | **SILICON**  | Physical die measured and characterised on a board. |

---

## Current rung for φ-anchor

| Subsystem | Rung reached | Evidence in repo |
|-----------|--------------|------------------|
| Canonical 0x47C0 GF16 dot4 anchor   | **GDS / TAPEOUT** | [`src/gf16_dot4.v`](src/gf16_dot4.v), [`test/tb.v`](test/tb.v), [`.github/workflows/test.yaml`](.github/workflows/test.yaml), [`.github/workflows/gds.yaml`](.github/workflows/gds.yaml), shuttle entry in [`CHANGELOG.md`](CHANGELOG.md) |
| Lucas L₂..L₇ POST (proves φ²+φ⁻²=3) | **SYNTH**         | [`src/phi_anchor_post.v`](src/phi_anchor_post.v), [`src/lucas_rom.v`](src/lucas_rom.v) |
| CLARA Gap-4 restraint controller     | **SYNTH**         | [`src/restraint_ctrl.v`](src/restraint_ctrl.v) |
| Sacred / Crown47 ROMs                | **SYNTH**         | [`src/sacred_constants_rom.v`](src/sacred_constants_rom.v), [`src/crown47_rom.v`](src/crown47_rom.v) |
| Friend/Foe TRN handshake             | **SYNTH**         | [`src/trinity_friend_foe.v`](src/trinity_friend_foe.v) |
| HWRNG (LFSR-based)                   | **SYNTH**         | [`src/hwrng_lfsr.v`](src/hwrng_lfsr.v) |
| v1.0.0 GF formats / quantizers / power modules | **RTL** (compiled, not exercised in `test/tb.v`) | `info.yaml` source list; modules in `src/` |
| **SILICON**                          | **NOT REACHED**   | No measured-die data lives in this repository. |

Reading this table: the chip has been **submitted** to the TTSKY26b shuttle
(CHANGELOG entry 2026-05-17), but no physical-silicon characterisation has
been added. Any TOPS/W or energy/op number outside of architecture
projections must therefore be treated as **projected, not measured**.

---

## CI evidence (live workflows)

| Workflow file | What it proves | Gate |
|---|---|---|
| [`.github/workflows/test.yaml`](.github/workflows/test.yaml)       | Canonical anchor 0x47C0 emitted on `{uio_out, uo_out}` after reset; cocotb suite green; Yosys reports no `$mul`. | SIM |
| [`.github/workflows/no_star.yaml`](.github/workflows/no_star.yaml) | R-SI-1: zero new `*` operators in synthesisable RTL (legacy `gf16_mul.v` grandfathered, XOR-based). | SPEC compliance |
| [`.github/workflows/fpga.yaml`](.github/workflows/fpga.yaml)       | Yosys synthesis of top module succeeds; Verilator lint `-Wall` clean; resource report uploaded. | SYNTH |
| [`.github/workflows/gds.yaml`](.github/workflows/gds.yaml)         | `tt-gds-action@ttsky26b` produces GDS, runs TT precheck, GL test, uploads `tt_submission`. | GDS / TAPEOUT |
| [`.github/workflows/sky130-nightly.yml`](.github/workflows/sky130-nightly.yml) | Nightly SKY130A regression. | GDS |
| [`.github/workflows/tri-test.yml`](.github/workflows/tri-test.yml) | Cross-die TRI-NET consistency check (anchor parity). | SPEC |

If a workflow badge is red, **trust the badge over this document**.

---

## Immediate checklist (what would move us up the ladder)

- [ ] **SILICON-1** — receive packaged TTSKY26b die, photograph, log lot/wafer.
- [ ] **SILICON-2** — bring up canonical 0x47C0 on a TT demo board; capture scope trace.
- [ ] **SILICON-3** — exercise Lucas POST (`ui_in[3:1]` sweep over L₂..L₇), record `phi_post_ok`.
- [ ] **SILICON-4** — power-rail sweep with `restraint_mode=1` vs `=0`; log current draw.
- [ ] **SYNTH-1**   — extend `test/tb.v` to cover v1.0.0 GF8/GF20/GF24/GF32/GF64/GF128/GF256 adders and the eight quantizers listed in `info.yaml`.
- [ ] **SYNTH-2**   — gate-level (GL) sim of full pinout including POST status path.
- [ ] **SPEC-1**    — finalise `specs/numeric/formats.t27` cross-check vs `conformance/FORMAT-SPEC-001.json`.
- [ ] **DOC-1**     — link board-bring-up notes once SILICON-1 is reached (will live in [`BENCHMARKS.md`](BENCHMARKS.md)).
- [ ] **SPEC-D2D-1** — promote [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) §4 (holographic-routing extension) from draft to a versioned sibling of [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) once an integrator commits to writing the RTL.
- [ ] **SPEC-NMSE-1** — land the harness contracted by [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) and emit a first report under `bench/nmse/`.
- [ ] **SPEC-DECK-1** — fill out [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) §4.1 (RBB) and §4.2 (CAP_BOOST) with `specs/fpga/*.t27` stubs *before* any RTL is opened.
- [ ] **SPEC-22FDX-1** — author the projection notebook described in [`TOPS_W_22FDX_PROJECTION.md`](TOPS_W_22FDX_PROJECTION.md) §4 (`bench/22fdx/`), so the 28–120 TOPS/W band is reproducible.

### Next-lineup spec docs (no new RTL claimed)

The following docs landed in this revision; they reorganise existing
spec material and add planned-only sections. None of them add
hardware:

- [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) — φ-anchor role layer for D2D / holographic chip-to-chip.
- [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) — NMSE protocol vs bfloat16, anchored to φ provenance.
- [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) — RBB / FBB / CAP_BOOST honest status.
- [`TRI_NET_API.md`](TRI_NET_API.md) — external-integration index.
- [`WHITEPAPER.md`](WHITEPAPER.md) — narrative hub.
- [`TOPS_W_22FDX_PROJECTION.md`](TOPS_W_22FDX_PROJECTION.md) — projection / Zenodo bundle plan.
- [`docs/SCIENTIFIC_IMPROVEMENT_PLAN.md`](docs/SCIENTIFIC_IMPROVEMENT_PLAN.md) — 2026 plan (CL-01..CL-04, EN-01..EN-03, SN-01..SN-03, PUB-01..PUB-03, OS-01..OS-03). All targets labelled `target` / `projection` / `VERIFY`.

> **Note on prior CI debt.** Earlier revisions of this file tracked three "CI-N" items (the v1.0.0 R-SI-1 violations in `avs_controller_96.v` / `fbb_active_path.v` / `int4_quantizer.v` / `nf4_quantizer.v` / `purkinje_thermal_gate.v`, the malformed `gf_formats.v` header, and the resulting `gds` red). Those are now **resolved on `main`** (commits `9c50309 fix: R-SI-1 compliance + Verilog-2005 syntax for GDS green` and `f174cf4 fix: synthesis translate_on pragma in lane_l_precheck.v`). No action needed from this docs PR.

This list is intentionally short; expand only when an item is completed and a
new gap becomes the next-best move.

---

## What is explicitly NOT claimed here

- **No measured TOPS/W.** The Green-AI section of [`README.md`](README.md) frames
  TOPS/W as an *architecture target* at an advanced node (22FDX projection),
  not a SKY130A demonstrator measurement. This document inherits that framing.
- **No measured power / energy-per-op on silicon.** Power-module RTL
  (`avs_controller_96.v`, `fbb_active_path.v`, `purkinje_thermal_gate.v`)
  is committed but unverified on a real die.
- **No formal proof in this repo's `coq/` and `trios-coq/` trees beyond what
  is committed there.** Proof status follows the source files in those
  directories — see [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md).

---

## Sibling repos

The φ-anchor is the **entry SKU** of TRI-NET; sibling chips and the toolchain
have their own STATUS files (each grades itself independently):

- [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) — 8×2 e-engine (safety/control engine).
- [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma) — 8×4 γ-surface (32-PE ternary mesh).
- `t27` — spec-to-RTL toolchain and numeric format registry (see [`specs/numeric/`](specs/numeric/)).

See [`LINEUP.md`](LINEUP.md) for the full positioning.

