# TRI-1 Nano — Single-tile Trinity GF16 MAC

> 🌳 Trinity role: **BRANCH-SILICON** — TTSKY26b shuttle SKU 1 of 3.
> Sibling of [tt-trinity-gf16](https://github.com/gHashTag/tt-trinity-gf16) (Mid) and [tt-trinity-max](https://github.com/gHashTag/tt-trinity-max) (Max).
> Spec: [TRI_NET_SHUTTLE_TRIAD](https://github.com/gHashTag/tt-trinity-gf16/blob/main/docs/architecture/TRI_NET_SHUTTLE_TRIAD.md) · EPIC [trinity-fpga#49](https://github.com/gHashTag/trinity-fpga/issues/49) L-DPC7.

**Anchor:** φ² + φ⁻² = 3 · DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)

## What it is

The smallest, simplest, most-likely-to-tape-out cleanly member of the
**TRI-1 Triad** — three Trinity ternary-MAC silicon dies submitted to the
same TinyTapeout shuttle (TTSKY26b, close 2026-05-18):

| SKU | Repo | Tiles | Modules | Role |
|-----|------|-------|---------|------|
| **Nano** | this | 1×1 | 5 (1 tile + GF16 leaves) | floor of the family — must close |
| **Mid**  | [tt-trinity-gf16](https://github.com/gHashTag/tt-trinity-gf16) | 8×2 | 15 SUPER-CROWN modules + GF16 mesh + BLAKE3 + ternary matmul + Lucas POST + BPB counter + Wishbone | flagship |
| **Max**  | [tt-trinity-max](https://github.com/gHashTag/tt-trinity-max) | (TBD) 4×4 mesh | full mesh-of-meshes, target stretch | stretch goal |

All three drive the **same canonical 16-bit constant `0x47C0`** on
`{uio_out, uo_out}` immediately after reset, computed from the same
hard-coded `dot4(1.0, 2.0, 3.0, 4.0)` in GF16. That equality is the
cross-die anchor of **TG-TRIAD-X (Theorem 36.1)** in
[PhD chapter 36](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex).

## Architecture

```
                 ┌──────────────────────────────────────────┐
   ui_in[0]      │       tt_um_trinity_nano (top)           │
   load_mode ───►│                                          │
   ui_in[7]      │   ┌───────────────────────────────────┐  │
   load_strobe ─►│   │ canonical gf16_dot4(1,2,3,4)      │  │ ──► uo_out[7:0]   = 0xC0
   ui_in[6]      │   │   (combinational, always live)    │  │     uio_out[7:0]  = 0x47
   compute_s ───►│   └───────────────────────────────────┘  │
                 │                                          │
   uio_in[7:0]   │   ┌───────────────────────────────────┐  │
   operand ─────►│   │ trinity_gf16_tile #(TILE_ID=0)    │──┼──► uo_out / uio_out
                 │   │ packet path (LOAD_A, COMPUTE,     │  │     when load_mode=1
                 │   │  RESULT, RECEIPT)                 │  │
                 │   └───────────────────────────────────┘  │
                 └──────────────────────────────────────────┘
```

- **`load_mode = 0` (default):** output pins always present `0x47C0`. This
  is what the TT test harness samples on the first cycle after reset, and
  it is what the **TG-TRIAD-X canonical job** observes from all three dies.
- **`load_mode = 1`:** rising edges on `ui_in[7]` clock the byte on
  `uio_in` into operand-A lanes 0…3 of the internal tile; a rising edge on
  `ui_in[6]` then issues a `COMPUTE` packet. Result appears on the
  `uo_out`+`uio_out` pins on the next cycle.

## Hard constraints (Silicon Invariants)

| Rule | Statement | Enforced by |
|------|-----------|-------------|
| **R-SI-1** | 0 new `*` operators in synthesisable RTL | Code review; gf16_mul is XOR-based |
| **R-SI-2** | 0 DSP / multiplier macros | OpenLane2 reports |
| **R-SI-3** | WNS ≥ 0 ns at 50 MHz on SKY130A | OpenLane2 STA |
| **R-SI-4** | DRC-clean (0 violations) | OpenLane2 KLayout DRC |
| **R-SI-5** | LVS-clean | OpenLane2 LVS |
| **R-SI-6** | Apache-2.0 only, no vendor IP | LICENSE + source headers |

## Build

```bash
# Local simulation (iverilog)
cd test
make
```

```bash
# GDS via GitHub Actions
git push
# → triggers .github/workflows/gds.yaml
# → OpenLane2 (SKY130A) → DRC + LVS + STA → uploads gds_artifact
```

## Pin mapping

See [`info.yaml`](info.yaml) for the canonical map. Summary:

- `ui_in[0]`  — `load_mode`
- `ui_in[6]`  — `compute_strobe`
- `ui_in[7]`  — `load_lane_strobe`
- `uio_in`    — operand byte (low 8 bits of GF16 element)
- `uo_out`    — result[7:0]
- `uio_out`   — result[15:8]
- `uio_oe`    — `8'hFF` (always drive)

## Provenance

- **License:** Apache-2.0 (see [LICENSE](LICENSE))
- **DOI:** [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
- **Author:** Dmitrii Vasilev <admin@t27.ai>, ORCID [0009-0008-4294-6159](https://orcid.org/0009-0008-4294-6159)
- **Defense:** 2026-06-15
- **Shuttle:** TinyTapeout TTSKY26b, close 2026-05-18

## See also

- Mid SKU: [tt-trinity-gf16](https://github.com/gHashTag/tt-trinity-gf16)
- PhD chapter: [`flos_70.tex` — Ch. 36 TRI-1 Triad](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex)
- EPIC: [trinity-fpga#49 L-DPC7](https://github.com/gHashTag/trinity-fpga/issues/49)
- Throne: [trios#264 Queen's Registry](https://github.com/gHashTag/trios/issues/264)
