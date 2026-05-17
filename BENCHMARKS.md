# BENCHMARKS — tt-trinity-phi (φ-anchor)

> Conservative, evidence-only benchmarks for the φ-anchor reference chip.
> Every row in this document is one of:
>
> - **MEASURED** — exercised by a CI workflow or local simulation that lives
>   in this repository, with the source path given.
> - **PROJECTED** — an architecture-level estimate from RTL structure or
>   from the v1.0.0 module set; clearly labelled, never confused with
>   silicon results.
> - **NOT MEASURED** — physical-silicon characterisation has not been
>   added to this repo. No silicon TOPS / energy numbers are claimed here.

If you need raw vendor-style TOPS, see [`COMPETITORS.md`](COMPETITORS.md);
this file deliberately resists that framing.

---

## What is measured today (MEASURED rows)

Everything in this section can be reproduced from the repo and a working
`iverilog` + `yosys` + `verilator` install. CI runs the same flows on every
push.

| ID | Metric | Result | Evidence |
|---|---|---|---|
| M-1 | Canonical anchor `dot4(1.0, 2.0, 3.0, 4.0)` in GF16(2⁴) on `{uio_out, uo_out}` after reset, `load_mode=0`. | `0x47C0` | [`src/gf16_dot4.v`](src/gf16_dot4.v), [`test/tb.v`](test/tb.v), [`.github/workflows/test.yaml`](.github/workflows/test.yaml) job *IVerilog canonical anchor test* |
| M-2 | `uio_oe == 0xFF` after reset (all `uio` lines driven). | Pass | Same as M-1. |
| M-3 | Cocotb RTL suite (`test/test.py` via `test/Makefile`, `SIM=icarus`). | Pass | [`.github/workflows/test.yaml`](.github/workflows/test.yaml) job *Cocotb RTL tests*. |
| M-4 | Yosys synth of `tt_um_trinity_nano` reports **no `$mul` cells** (R-SI-1). | Pass | [`.github/workflows/test.yaml`](.github/workflows/test.yaml) job *R-SI-1 audit (Yosys)*. |
| M-5 | R-SI-1 grep audit: no new `*` operators in `src/` (legacy `gf16_mul.v` grandfathered, XOR-based). | Pass | [`.github/workflows/no_star.yaml`](.github/workflows/no_star.yaml). |
| M-6 | Yosys synthesis of top module completes; resource report uploaded. | Pass | [`.github/workflows/fpga.yaml`](.github/workflows/fpga.yaml). |
| M-7 | Verilator `--lint-only -Wall -Wno-fatal` lint on `tt_um_trinity_nano.v`. | Pass | [`.github/workflows/fpga.yaml`](.github/workflows/fpga.yaml) job *Verilator lint*. |
| M-8 | OpenLane2 (SKY130A) `tt-gds-action@ttsky26b` produces `tt_submission` artefact; TT precheck + GL test green. | Pass | [`.github/workflows/gds.yaml`](.github/workflows/gds.yaml). |
| M-9 | Lucas POST chain (L₂=3, L₃=4, L₄=7, L₅=11, L₆=18, L₇=29) — proves φ²+φ⁻²=3 via Binet. | Pass in simulation | [`src/phi_anchor_post.v`](src/phi_anchor_post.v), [`src/lucas_rom.v`](src/lucas_rom.v); exercised by [`test/tb.v`](test/tb.v) and the README's `tb_post` recipe. |
| M-10 | Cross-die TRI-NET consistency check (anchor parity + R-SI-1 audit). | Pass | [`.github/workflows/tri-test.yml`](.github/workflows/tri-test.yml). |

---

## Cell-count snapshot (PROJECTED, from RTL structure)

Per-module estimates from the README architecture section; these are *RTL
intent*, not post-synth cell counts. To get the latter, download the
`resources-report` artefact uploaded by [`fpga.yaml`](.github/workflows/fpga.yaml).

| Module | Estimated cells | Source file |
|---|---:|---|
| `gf16_dot4` (canonical 0x47C0) | ~50 | [`src/gf16_dot4.v`](src/gf16_dot4.v) |
| `gf16_mul` (legacy XOR-based) | ~50 | [`src/gf16_mul.v`](src/gf16_mul.v) |
| `trinity_gf16_tile` (packet path) | ~250 | [`src/trinity_gf16_tile.v`](src/trinity_gf16_tile.v) |
| `phi_anchor_post` (Lucas POST) | ~120 | [`src/phi_anchor_post.v`](src/phi_anchor_post.v) |
| `lucas_rom` | ~30 | [`src/lucas_rom.v`](src/lucas_rom.v) |
| `hwrng_lfsr` | ~20 | [`src/hwrng_lfsr.v`](src/hwrng_lfsr.v) |
| `restraint_ctrl` (Gap-4 sketch) | ~100 | [`src/restraint_ctrl.v`](src/restraint_ctrl.v) |
| `sacred_constants_rom` (75 constants, sparse) | ~133 | [`src/sacred_constants_rom.v`](src/sacred_constants_rom.v) |
| `crown47_rom` | ~100 | [`src/crown47_rom.v`](src/crown47_rom.v) |
| `trinity_friend_foe` | ~30 | [`src/trinity_friend_foe.v`](src/trinity_friend_foe.v) |
| `gf16_add` | ~20 | [`src/gf16_add.v`](src/gf16_add.v) |
| **Total (core, pre-v1.0.0)** | **~850 @ 60% density** | — |

v1.0.0 also bundles GF4..GF256 adders, eight quantizers, and three power
modules (see [`info.yaml`](info.yaml)). They are RTL-committed and
compiled by CI, but `test/tb.v` does not yet exercise each of them
individually — see the SYNTH-1 item in [`STATUS.md`](STATUS.md#immediate-checklist-what-would-move-us-up-the-ladder).

---

## What is NOT measured (NOT MEASURED rows)

| ID | Metric | Status |
|---|---|---|
| N-1 | Measured TOPS / TOPS-per-watt on physical SKY130A die. | Not measured — no silicon characterisation in repo. |
| N-2 | Measured energy-per-op on packaged die. | Not measured. |
| N-3 | Worst-case slack (WNS) on packaged die. | Not measured (CI reports synth-level STA via OpenLane2; that is *not* a silicon measurement). |
| N-4 | Power-rail sweep under `restraint_mode`. | Not measured. |
| N-5 | Yield / DPM. | Not measured. |
| N-6 | Throughput on a representative LLM / CNN workload. | Not measured (this chip is not a workload accelerator; see [`LINEUP.md`](LINEUP.md)). |

These should not be quoted from any other document (including the README's
Green-AI section) without the qualifying labels used there
("architecture target", "peer-review pending").

---

## Architecture projections (PROJECTED, from RTL intent only)

Restated honestly from [`README.md` § Green AI Manifesto](README.md#green-ai-manifesto):

| Metric | Measured (SKY130A, 130 nm) | Architecture target (22FDX 22 nm projection) |
|---|---|---|
| TOPS/W | Proof-of-concept node, **not a peak-TOPS number** | 28–120 TOPS/W (peer-review pending) |
| Energy/op | Educational-node figure, **not a peak figure** | Competitive vs commercial edge NPUs at advanced node |

The projection is **architecture-level**, not silicon. It is included so
that readers comparing this repo against [`COMPETITORS.md`](COMPETITORS.md)
understand where TRI-NET intends to sit *at a real node*, not at 130 nm.

If a future commit adds measured-silicon data, it should land as new
**MEASURED** rows in the table at the top — not as edits to this section.

---

## How to reproduce M-1..M-10 locally

```bash
# Anchor test (M-1, M-2)
iverilog -I src -o /tmp/tb.out src/*.v test/tb.v
vvp /tmp/tb.out  # expect 0x47C0 in the canonical position

# Cocotb suite (M-3)
cd test && make SIM=icarus

# R-SI-1 audit (M-4, M-5)
grep -nE '\*' src/*.v | grep -v gf16_mul.v | grep -v '//' || echo "R-SI-1 PASS"
yosys -p "read_verilog -I src src/*.v; hierarchy -top tt_um_trinity_nano; \
          proc; opt; stat" | grep '\$mul' || echo "no multipliers (R-SI-1 OK)"

# Synth + lint (M-6, M-7)
yosys -p "read_verilog -I src src/*.v; hierarchy -top tt_um_trinity_nano; \
          proc; opt; synth -top tt_um_trinity_nano; stat"
verilator --lint-only -Wall -Wno-fatal -Isrc -y src src/tt_um_trinity_nano.v
```

For M-8 / M-9 / M-10, push to a fork — the workflows do the rest.

---

## See also

- [`STATUS.md`](STATUS.md) — readiness ladder; what would move us off
  SYNTH/GDS toward SILICON.
- [`COMPETITORS.md`](COMPETITORS.md) — why peak-TOPS comparisons are not
  the axis we compete on.
- [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md) — assurance evidence
  map.
- [`LINEUP.md`](LINEUP.md) — full TRI-NET line and how φ-anchor relates
  to euler / gamma / t27.
