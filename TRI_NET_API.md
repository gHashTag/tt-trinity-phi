# TRI_NET_API — External Integration Notes (φ-anchor view)

> **Readiness:** **SPEC**, summarising existing material. This file is
> the **integration index** for tools and bridges that want to talk to
> the φ-anchor chip (or any TRI-NET die) from the outside. It does not
> introduce a new API surface — it points to the authoritative specs
> that already live in this repo, and adds the line-level framing.

Last updated: 2026-05-18.

---

## 1. Audience

You are writing one of:

- A **host bridge** (MCU / FPGA / USB device) that drives the φ-anchor
  pin interface directly.
- A **fabric bridge** that mediates between TRI-NET dies on the
  TTSKY26b DevKit board.
- An **automated tester / CI integration** that wants to assert
  the canonical `0x47C0` cross-die anchor.
- A **research integration** that consumes the t27 numeric registry
  to build NMSE harnesses or downstream models.

For any of these, the φ-anchor side of the API is defined by:

| Layer | Spec | What it nails down |
|-------|------|--------------------|
| **Pin interface**        | [`docs/API.md`](docs/API.md), [`docs/PINOUT.md`](docs/PINOUT.md) | `ui_in / uo_out / uio` semantics in canonical and load modes. |
| **Wire-level D2D**       | [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md), [`docs/CROSS_TILE_INTERCONNECT.md`](docs/CROSS_TILE_INTERCONNECT.md) | LOAD_MODE / SYNC_STROBE / ACK timing, frame format. |
| **φ-anchor role layer**  | [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) | Anchor / provenance / control endpoint responsibilities. |
| **Numeric registry**     | [`specs/numeric/formats.t27`](specs/numeric/formats.t27), [`docs/TRI_NET_FORMATS_SUMMARY.md`](docs/TRI_NET_FORMATS_SUMMARY.md) | GF4..GF256 + fp/bf/int/posit/ternary formats. |
| **NMSE harness contract** | [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) | How an external NMSE benchmark must report against φ-anchor provenance. |
| **Hardware bring-up**    | [`docs/HARDWARE_BRINGUP.md`](docs/HARDWARE_BRINGUP.md), [`docs/HARDWARE-IMPLEMENTATION.md`](docs/HARDWARE-IMPLEMENTATION.md) | Board-level expectations once silicon arrives. |
| **DevKit demo**          | [`docs/DEVKIT_DEMO.md`](docs/DEVKIT_DEMO.md) | Reference firmware plan for an external host. |

This file is the front door; the linked documents are normative.

---

## 2. Minimum-viable external integration

The smallest useful external integration with φ-anchor is **verify the
canonical anchor**. Required steps:

1. Hold `rst_n` low ≥ 2 clocks, then release.
2. Drive `ui_in[0] = 0` (canonical mode), `ena = 1`, `clk` at any rate
   in the documented range.
3. Sample `{uio_out[7:0], uo_out[7:0]}` on the next cycle.
4. Assert it equals **`0x47C0`**.

If this fails, **do not proceed** with any further D2D / compute
operations. φ-anchor is the gate.

Reproducible-in-software equivalent (no hardware):

```bash
iverilog -I src -o /tmp/tb.out src/*.v test/tb.v
vvp /tmp/tb.out   # canonical 0x47C0 expected
```

---

## 3. Versioning & stability

| API surface | Version | Stability |
|-------------|---------|-----------|
| Pin interface (`ui_in / uo_out / uio`)         | TTSKY26b   | Frozen for v1.0 silicon. |
| Wire-level D2D (`LOAD_MODE / SYNC_STROBE / ACK`) | TIP v1.0 | Frozen — see [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) §1.3. |
| Frame format byte layout                       | TIP v1.0   | Frozen; v1.1+ via the VERSION_FIELD bit (currently 0). |
| Canonical anchor word                          | TG-TRIAD-X | Frozen by Theorem 36.1 — `0x47C0`. |
| t27 numeric registry                           | repo HEAD  | Per-format SHA pinned by NMSE reports (see [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) §5). |
| φ-anchor role layer ([`D2D_PROTOCOL.md`](D2D_PROTOCOL.md)) | draft | SPEC; next-lineup extensions explicitly marked planned. |

The "frozen" rows must not change without a new TTSKY26b-equivalent
shuttle commit and a CHANGELOG entry.

---

## 4. What is **not** an API

To avoid scope creep when external integrators read this repo, the
following are explicitly NOT part of the integration surface:

- **Internal RTL modules** (`gf16_dot4`, `phi_anchor_post`, etc.) — they
  may be refactored without notice. Use the pin interface.
- **Synth artefacts and OpenLane2 step output** — not stable.
- **Estimated cell counts and projected TOPS/W** — not measurements.
  See [`BENCHMARKS.md`](BENCHMARKS.md).
- **Sacred opcode mappings beyond what's listed in `docs/API.md`** —
  treat any sacred opcode not in `docs/API.md` as private.

---

## 5. Reporting integration issues

- File a GitHub issue against [tt-trinity-phi](https://github.com/gHashTag/tt-trinity-phi)
  with the verification step that failed and the report identifiers
  from `GF16_BFLOAT16_NMSE.md` if applicable.
- Cross-die issues (anchor mismatch) should also reference the sibling
  repo whose die produced the wrong value:
  [tt-trinity-euler](https://github.com/gHashTag/tt-trinity-euler) /
  [tt-trinity-gamma](https://github.com/gHashTag/tt-trinity-gamma).
- For protocol-layer ambiguity, link the section of
  [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md)
  rather than re-describing it.

---

## 6. Cross-references

- [`docs/API.md`](docs/API.md) — pin-level API (authoritative).
- [`docs/PINOUT.md`](docs/PINOUT.md) — pinout & timing.
- [`docs/INTERCONNECT_PROTOCOL_V1.md`](docs/INTERCONNECT_PROTOCOL_V1.md) — frozen TIP v1.0 spec.
- [`docs/CROSS_TILE_INTERCONNECT.md`](docs/CROSS_TILE_INTERCONNECT.md) — board wiring.
- [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) — φ-anchor role layer.
- [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) — NMSE harness contract.
- [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) — power-deck status (affects bring-up).
- [`STATUS.md`](STATUS.md) — readiness ladder.
- [`LINEUP.md`](LINEUP.md) — line-level positioning.
- [`WHITEPAPER.md`](WHITEPAPER.md) — value proposition & whitepaper hub.
