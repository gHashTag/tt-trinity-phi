# PINOUT — TRI-1 Phi (tt_um_trinity_nano)

**Project:** TRI-1 Phi — Trinity φ-anchor 1×1 Lucas POST + CLARA Gap-4  
**Tile:** 1×1 · Tiny Tapeout SKY130A (TTSKY26b, slot #4914)  
**Top module:** `tt_um_trinity_nano`  
**Clock:** 50 MHz · **Reset:** active-low `rst_n`  
**Canonical anchor:** `0x47C0` on `{uio_out[7:0], uo_out[7:0]}` after reset (Theorem 36.1, TG-TRIAD-X)

> Cross-tile interconnect details: see [`docs/CROSS_TILE_INTERCONNECT.md`](CROSS_TILE_INTERCONNECT.md)

---

## Pin Table

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                  TRI-1 Phi (tt_um_trinity_nano) — 1×1 tile                 │
 │                                                                             │
 │  PIN       DIR    SIGNAL / FUNCTION                                         │
 │  ────────  ─────  ──────────────────────────────────────────────────────    │
 │  ui[0]     IN     load_mode                                                 │
 │                     0 = canonical mode: 0x47C0 on {uio_out,uo_out}          │
 │                         POST status; lucas_idx reads Lucas ROM              │
 │                     1 = packet path: ui[7:1] carry lane/strobe data         │
 │  ui[1]     IN     lucas_idx[0] — Lucas ROM L_n address bit 0               │
 │                     (index selects L2..L7; valid range 0–5)                 │
 │  ui[2]     IN     lucas_idx[1] — Lucas ROM L_n address bit 1               │
 │  ui[3]     IN     lucas_idx[2] — Lucas ROM L_n address bit 2               │
 │  ui[4]     IN     rng_ena — advance HWRNG LFSR each clock cycle            │
 │  ui[5]     IN     restraint_mode — activate CLARA Gap-4 bounded            │
 │                     rationality controller                                  │
 │  ui[6]     IN     compute_strobe — rising edge issues COMPUTE               │
 │  ui[7]     IN     load_lane_strobe — rising edge advances lane              │
 │  ────────  ─────  ──────────────────────────────────────────────────────    │
 │  uo[0]     OUT    result[0]   — canonical 0x47C0[0]  (default = 0)         │
 │  uo[1]     OUT    result[1]   — canonical 0x47C0[1]  (default = 0)         │
 │  uo[2]     OUT    result[2]   — canonical 0x47C0[2]  (default = 0)         │
 │  uo[3]     OUT    result[3]   — canonical 0x47C0[3]  (default = 0)         │
 │  uo[4]     OUT    result[4]   — canonical 0x47C0[4]  (default = 0)         │
 │  uo[5]     OUT    result[5]   — canonical 0x47C0[5]  (default = 0)         │
 │  uo[6]     OUT    result[6]   — canonical 0x47C0[6]  (default = 1)         │
 │  uo[7]     OUT    result[7]   — canonical 0x47C0[7]  (default = 1)         │
 │  ────────  ─────  ──────────────────────────────────────────────────────    │
 │  uio[0]    OUT    result[8]   — canonical 0x47C0[8]  (default = 0)         │
 │  uio[1]    OUT    result[9]   — canonical 0x47C0[9]  (default = 0)         │
 │  uio[2]    OUT    result[10]  — canonical 0x47C0[10] (default = 0)         │
 │  uio[3]    OUT    result[11]  — canonical 0x47C0[11] (default = 0)         │
 │  uio[4]    OUT    result[12]  — canonical 0x47C0[12] (default = 0)         │
 │  uio[5]    OUT    result[13]  — canonical 0x47C0[13] (default = 1)         │
 │  uio[6]    OUT    result[14]  — canonical 0x47C0[14] (default = 0)         │
 │  uio[7]    OUT    result[15]  — canonical 0x47C0[15] (default = 0)         │
 └─────────────────────────────────────────────────────────────────────────────┘
```

### Canonical default: 0x47C0

```
  {uio_out[7:0], uo_out[7:0]} = 16'h47C0
  Binary: 0100_0111_1100_0000
  Meaning: dot4(1.0, 2.0, 3.0, 4.0) in GF16 ternary encoding
  Theorem 36.1 cross-die anchor: φ² + φ⁻² = 3 (Lucas identity)
```

---

## Pin Function Details

| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| ui[0] | `load_mode` | IN | Core mode select. Pull low for POST/canonical; drive high to enable packet path. First pin tested during bring-up. |
| ui[1] | `lucas_idx[0]` | IN | LSB of 3-bit Lucas ROM address. L₂=0, L₃=1, L₄=2, L₅=3, L₆=4, L₇=5. |
| ui[2] | `lucas_idx[1]` | IN | Mid bit of Lucas index. |
| ui[3] | `lucas_idx[2]` | IN | MSB of Lucas index. Indices 6–7 are reserved/clamped to L₇. |
| ui[4] | `rng_ena` | IN | Pulse high to clock the HWRNG LFSR. Die-unique nonce generation. |
| ui[5] | `restraint_mode` | IN | Activates CLARA Gap-4 bounded rationality controller. When high, output is gated through `restraint_ctrl`. |
| ui[6] | `compute_strobe` | IN | Rising edge triggers ternary dot4 MAC computation. Requires valid lane data first. |
| ui[7] | `load_lane_strobe` | IN | Rising edge advances the active lane register. Use with `load_mode=1` to shift in data. |
| uo[7:0] | `result[7:0]` | OUT | Low byte of 16-bit result. Canonical: `0xC0` (post-reset). |
| uio[7:0] | `result[15:8]` | OUT | High byte of 16-bit result. Canonical: `0x47` (post-reset). |

### Status bits in canonical mode (load_mode=0)

When `load_mode=0`:
- `uo_out[7:0]` = `result[7:0]` (defaults to `0xC0` — low byte of `0x47C0`)
- `uio_out[7:0]` = `result[15:8]` (defaults to `0x47` — high byte of `0x47C0`)
- Additional status: `status_request[3]` is encoded in `result[11]`, `status_request[2]` in `result[10]` (verify against `phi_anchor_post.v`)

---

## Clock and Reset Specification

| Parameter | Value |
|-----------|-------|
| Clock frequency | 50 MHz (target) |
| Clock period | 20 ns |
| Reset polarity | Active-low (`rst_n`) |
| Reset minimum pulse | 2 clock cycles minimum |
| Reset release | Synchronous release recommended |
| Post-reset latency | ≤ 1 clock cycle to assert 0x47C0 |
| FPGA-validated frequency | 323 MHz (XC7A100T — headroom confirmed) |

---

## Bring-Up Sequence

```
Step 1 — RESET
  Assert rst_n=0 for ≥ 4 clock cycles (80 ns at 50 MHz).
  Hold ui[7:0] = 0x00 during reset.

Step 2 — CHECK CANONICAL ANCHOR (0x47C0)
  Release rst_n=1. Wait 1 clock cycle (20 ns).
  Read {uio_out[7:0], uo_out[7:0]}.
  Expected: 0x47C0
  If mismatch → FAULT (chip not passing POST gate).

Step 3 — POST (Power-On Self-Test)
  Set load_mode=0, lucas_idx={0,0,0} (address L₂).
  Assert compute_strobe rising edge.
  Read result. Expected: Lucas L₂ = 3 (phi² + phi⁻² = 3 identity).
  Iterate lucas_idx 0→5 to probe L₂..L₇; verify chain.
  All passing → POST COMPLETE.

Step 4 — OPERATIONAL MODE
  Set load_mode=1 to enable packet path.
  Use load_lane_strobe to shift data into lane registers.
  Assert compute_strobe to trigger ternary MAC.
  Read {uio_out, uo_out} for 16-bit result.
  Optionally set restraint_mode=1 to engage CLARA Gap-4.

Step 5 — CROSS-TILE SYNC (DevKit board)
  See CROSS_TILE_INTERCONNECT.md for 3-wire handshake
  between Phi (master), Euler (compute slave), Gamma (neuromorphic slave).
```

---

## Lucas ROM Addressing

| `lucas_idx[2:0]` | Lucas number | Value (decimal) |
|------------------|-------------|-----------------|
| 3'b000 | L₂ | 3 |
| 3'b001 | L₃ | 4 |
| 3'b010 | L₄ | 7 |
| 3'b011 | L₅ | 11 |
| 3'b100 | L₆ | 18 |
| 3'b101 | L₇ | 29 |
| 3'b110–3'b111 | Reserved | Clamped to L₇ |

The Lucas chain proves φ² + φ⁻² = 3 (Trinity algebraic identity, Theorem 36.1).

---

## Related Documents

- [`docs/CROSS_TILE_INTERCONNECT.md`](CROSS_TILE_INTERCONNECT.md) — Cross-tile interconnect spec for Phi/Euler/Gamma DevKit board
- DOI: [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877) — Trinity Stack provenance
- Sibling: [TRI-1 Euler (#4915)](https://tinytapeout.com/runs/ttsky26b/tt_um_ghtag_trinity_gf16) — e-engine 8×2
- Sibling: [TRI-1 Gamma (#4913)](https://tinytapeout.com/runs/ttsky26b/tt_um_trinity_max_true) — γ-surface 8×4
