# D2D_PROTOCOL — Holographic Chip-to-Chip Communication (φ-anchor view)

> **Readiness:** **SPEC (draft)** for the holographic-routing extension; the
> physical wire-level layer it sits on (3-wire LOAD_MODE / SYNC_STROBE /
> open-drain ACK) is already at GDS for TTSKY26b — see
> [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) and
> [`docs/CROSS_TILE_INTERCONNECT.md`](docs/CROSS_TILE_INTERCONNECT.md).
> Nothing in this file claims new hardware: it describes how φ-anchor
> **participates** in TRI-NET D2D as the **anchor / provenance / control
> endpoint**, and what the next-lineup holographic-routing extension would
> have to specify before any RTL is written.

Last updated: 2026-05-18.

---

## 1. Purpose & scope

This document is the φ-anchor-side spec for **die-to-die (D2D) holographic
chip-to-chip communication** across the TRI-NET line (φ-anchor / e-engine /
γ-surface). It exists to:

1. Make explicit which D2D responsibilities live on **φ-anchor** vs the
   other two dies, so that integrators can write a compatible bridge
   against this repo alone.
2. Pin down the **anchor / provenance / control** role of φ-anchor so it
   is not mistakenly treated as a compute slave.
3. Mark **what is implemented today** (rung-by-rung against
   [`STATUS.md`](STATUS.md)) vs **what is planned** for next-lineup, with
   no fabricated hardware claims.

This file does **not** redefine the wire-level protocol — that is frozen
for TTSKY26b in [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md).
It adds a φ-anchor-side **role** layer on top.

---

## 2. φ-anchor's three D2D roles

φ-anchor occupies three roles in the TRI-NET D2D fabric. None of them are
"compute slave" — that responsibility is on e-engine and γ-surface.

| Role | What it means | Evidence today |
|------|---------------|----------------|
| **Anchor endpoint**     | Emits the canonical `0x47C0` on `{uio_out, uo_out}` at reset (`load_mode=0`). Any other die in the fabric **MUST** cross-check its own `0x47C0` against the φ-anchor value before initiating compute. | [`src/gf16_dot4.v`](src/gf16_dot4.v), [`test/tb.v`](test/tb.v), [`.github/workflows/tri-test.yml`](.github/workflows/tri-test.yml) |
| **Provenance endpoint** | Provides die-unique nonce via `hwrng_lfsr`, Lucas-POST sticky-fail bit, and friend/foe handshake. Together these uniquely address a φ-anchor die on the fabric and let downstream dies sign receipts against it. | [`src/hwrng_lfsr.v`](src/hwrng_lfsr.v), [`src/phi_anchor_post.v`](src/phi_anchor_post.v), [`src/trinity_friend_foe.v`](src/trinity_friend_foe.v) |
| **Control endpoint**    | Holds the **master** position in the v1.0 interconnect state machine — drives `LOAD_MODE` / `SYNC_STROBE` and reads back the wired-AND ACK from the two slaves. Also carries the CLARA Gap-4 `restraint_ctrl`, which is the protocol-level kill-switch the fabric MUST honour. | [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) §4 (state machine), [`src/restraint_ctrl.v`](src/restraint_ctrl.v) |

These three roles are **separable**: a board could in principle wire only
one of them out (e.g. use φ-anchor purely as a provenance witness without
giving it bus master) — but the v1.0 protocol assigns all three to the
same chip because the proof seed and the master gate are on the same die.

---

## 3. What is implemented today (v1.0, TTSKY26b)

These are the D2D-relevant bits that are at **SYNTH** or **GDS** rung in
[`STATUS.md`](STATUS.md):

| Item | Rung | File |
|------|------|------|
| Canonical 0x47C0 anchor on `{uio_out, uo_out}` | GDS | [`src/gf16_dot4.v`](src/gf16_dot4.v) |
| Friend/foe handshake (`MY_ANCHOR=0xCF` for φ) | SYNTH | [`src/trinity_friend_foe.v`](src/trinity_friend_foe.v) |
| Lucas L₂..L₇ POST (provenance) | SYNTH | [`src/phi_anchor_post.v`](src/phi_anchor_post.v) |
| HWRNG die-unique nonce | SYNTH | [`src/hwrng_lfsr.v`](src/hwrng_lfsr.v) |
| CLARA Gap-4 `restraint_ctrl` (control endpoint) | SYNTH | [`src/restraint_ctrl.v`](src/restraint_ctrl.v) |
| 3-wire interconnect frame & state machine | SPEC | [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) |

**No holographic-routing RTL exists yet** in this repo. The
`holo_mux_x4` module ([`src/holo_mux_x4.v`](src/holo_mux_x4.v)) is an
**on-die** GF16 4:1 multiplexer for the LEVER STACK, not a D2D
holographic-router primitive. The naming overlap is deliberate (both come
from the "holographic" family of sacred opcodes) but the scope is
on-die-only.

---

## 4. What is NOT implemented (next-lineup, planned only)

The following are **planned / SPEC stubs** for a future lineup. None of
them have RTL in this repo. Marked here so an integrator does not assume
they exist.

### 4.1 Holographic chip-to-chip routing

| Item | Planned rung | Open question |
|------|--------------|---------------|
| Multi-chip GF16 fan-out via D2D (more than 1 slave) | SPEC stub | Wire C is wired-AND across 2 slaves today; scaling to N>2 needs a new arbitration scheme. |
| Holographic frame encoding (parity-spread payload across multiple D2D hops) | SPEC stub | Frame format in [`INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) §5 does not yet reserve a payload-spread bit. |
| Cross-board (off-PCB) D2D | SPEC stub | Out of scope for TTSKY26b; would need a physical-layer redefinition (LVDS, AC-coupled, etc.). |

### 4.2 φ-anchor's role in a holographic fabric

If a future lineup adds holographic routing, φ-anchor's role would
*extend* — not replace — the three roles in §2:

- **Anchor endpoint** stays the same: 0x47C0 still gates the bring-up.
- **Provenance endpoint** would also sign per-hop receipts (currently
  only signs at reset). This needs BLAKE3 / Ed25519 on-die, tracked
  separately in [`docs/PHI_ED25519_ROADMAP.md`](docs/PHI_ED25519_ROADMAP.md).
- **Control endpoint** would gain a "drain on restraint" semantic — if
  `restraint_ctrl` trips, the holographic fabric MUST drain in-flight
  frames before re-enabling. This is **not** in v1.0.

These extensions are deliberately listed as planned text, not as
features. They are also reflected as `SPEC-N` checkboxes in
[`STATUS.md`](STATUS.md).

---

## 5. Acceptance criteria for any next-lineup D2D PR

Before any holographic-D2D RTL is merged into this repo, the PR MUST:

1. Add a corresponding `.t27` numeric / behavioural spec under
   [`specs/`](specs/) (see [`specs/numeric/formats.t27`](specs/numeric/formats.t27)
   for the convention).
2. Update [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md)
   — or add a v1.1 sibling — that pins down the new wire / frame
   semantics, including version-negotiation behaviour (§1.3 of v1.0).
3. Add a row to [`BENCHMARKS.md`](BENCHMARKS.md) **MEASURED** table only
   once the new RTL is exercised by `test/tb.v` or a cocotb job in
   [`.github/workflows/`](.github/workflows/). Architecture estimates
   land in the **PROJECTED** section, never in MEASURED.
4. Preserve the canonical 0x47C0 cross-die anchor — any change that
   breaks `tri-test.yml` is a regression.
5. Honour R-SI-1 (no new `*` operators) — see
   [`.github/workflows/no_star.yaml`](.github/workflows/no_star.yaml).

If a PR cannot satisfy these, the change belongs in this **spec** file,
not in `src/`.

---

## 6. Cross-references

- [`STATUS.md`](STATUS.md) — readiness ladder; D2D-relevant rows.
- [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) — wire-level protocol (frozen at TTSKY26b).
- [`docs/CROSS_TILE_INTERCONNECT.md`](docs/CROSS_TILE_INTERCONNECT.md) — board-level wiring.
- [`docs/PHI_ED25519_ROADMAP.md`](docs/PHI_ED25519_ROADMAP.md) — on-die signing roadmap (touches §4.2).
- [`LINEUP.md`](LINEUP.md) — line-level positioning.
- [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) — numeric anchor that rides on top of D2D.
- [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) — power-rail stack referenced by §4.2.
- [`TRI_NET_API.md`](TRI_NET_API.md) — external-integration interface notes.
