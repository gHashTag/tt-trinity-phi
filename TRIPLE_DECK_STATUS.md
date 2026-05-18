# TRIPLE_DECK_STATUS — RBB → FBB → CAP_BOOST on φ-anchor

> **Readiness:** **mixed**, see table in §3. **FBB** is at SYNTH on
> φ-anchor today; **RBB** and **CAP_BOOST** are **planned, not
> implemented** — no RTL exists in `src/` for either. This document
> describes the φ-anchor side of the Triple-Deck power-rail stack so
> the line-level claim ("Triple-Deck on all chips") cannot be misread
> as already-true on φ-anchor.

Last updated: 2026-05-18.

---

## 1. What "Triple-Deck" means in TRI-NET

The Triple-Deck is a three-stage adaptive-bias stack applied to a chip's
power rails, intended for low-voltage operation at advanced nodes:

| Deck | Mechanism | Intent |
|------|-----------|--------|
| **RBB**       | Reverse Body Bias — raises Vth, cuts leakage in idle blocks. | Save standby power. |
| **FBB**       | Forward Body Bias — lowers Vth on active paths, restores speed at low V. | Recover speed in active windows. |
| **CAP_BOOST** | Decoupling-cap-assisted rail boost on demand (burst headroom). | Survive di/dt spikes without raising static V. |

The line-level value proposition is that all three TRI-NET chips ship
with the full RBB → FBB → CAP_BOOST stack. That is the **target**; this
file records what is **actually committed** on φ-anchor today.

---

## 2. Caveat: SKY130A vs the target node

The Triple-Deck only delivers its headline numbers at an **advanced
node** (the 22FDX projection in
[`BENCHMARKS.md`](BENCHMARKS.md#architecture-projections-projected-from-rtl-intent-only)).
At SKY130A (130 nm), body-bias swing is limited and CAP_BOOST headroom
is small. Anything in this file is therefore "RTL exists / spec exists",
not "characterised on SKY130A silicon".

The R5-honest rule applies: no measured TOPS / energy / leakage delta
from a real die is claimed here. See
[`BENCHMARKS.md`](BENCHMARKS.md) §"What is NOT measured".

---

## 3. φ-anchor Triple-Deck status (today)

| Deck | Rung on φ-anchor | Evidence in repo | Notes |
|------|------------------|------------------|-------|
| **RBB** (Reverse Body Bias)        | **Not implemented**       | none                                                    | No `src/rbb_*.v`. Planned only. Cell is a `0` in any aggregate count. |
| **FBB** (Forward Body Bias)        | **SYNTH**                 | [`src/fbb_active_path.v`](src/fbb_active_path.v)         | Sacred opcode 0xF2. Coq proof reference `FBBActive2.v` (proof status tracked in [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md)). Not exercised on silicon. |
| **CAP_BOOST** (Decap-assisted boost) | **Not implemented**       | none                                                    | No `src/cap_boost*.v`. Planned only. AVS-96 ([`src/avs_controller_96.v`](src/avs_controller_96.v)) handles adaptive voltage but does **not** implement CAP_BOOST. |
| **AVS-96 (adaptive voltage scaler)** *(adjacent, not a deck)* | **SYNTH** | [`src/avs_controller_96.v`](src/avs_controller_96.v) | Included for completeness; sometimes confused with CAP_BOOST. |
| **DFS gate**           *(adjacent)* | **SYNTH** | [`src/dfs_gate.v`](src/dfs_gate.v)                         | Frequency gating; orthogonal to the body-bias stack. |
| **Purkinje thermal gate** *(adjacent)* | **SYNTH** | [`src/purkinje_thermal_gate.v`](src/purkinje_thermal_gate.v) | Thermal trip; gates FBB at high leakage. |

Reading this table: φ-anchor implements **one of three** Triple-Deck
stages (FBB) plus several adjacent power-management blocks. It is
**not** a full Triple-Deck demonstrator. Any line-level marketing that
says "Triple-Deck on all chips" MUST be qualified for φ-anchor
specifically with this table.

---

## 4. Minimal-honesty plan to close the gap

The plan below is **plan only** — no RTL is committed here, and no PR
should claim a deck is "implemented" without a `src/*.v` file plus a
`test/tb.v` cocotb exercise that proves the behaviour at SIM rung.

### 4.1 RBB on φ-anchor (planned)

- Add `specs/fpga/rbb_idle_path.t27` defining opcode, idle-detect input,
  Vth bump levels, and re-entry latency. Mirror the structure of
  [`specs/fpga/fbb_active_path.t27`](specs/fpga/fbb_active_path.t27).
- Then add `src/rbb_idle_path.v` once the spec lands.
- Then add a cocotb job that holds an idle window, asserts RBB, and
  reads back leakage-monitor delta in simulation.
- Order **MUST** be SPEC → RTL → SIM, gated by R-SI-1.

### 4.2 CAP_BOOST on φ-anchor (planned)

- Add `specs/fpga/cap_boost.t27` defining burst-trigger input,
  reservoir-cap parameters (architectural only — SKY130A cannot host the
  real cap), and rail-droop fallback.
- Then `src/cap_boost.v` stub.
- This deck is **fundamentally an analog/process feature**; the digital
  RTL is only the controller. The doc MUST say so to avoid claiming
  silicon behaviour the open PDK cannot deliver.

### 4.3 Verifying FBB beyond SYNTH

The remaining FBB work is to exercise [`src/fbb_active_path.v`](src/fbb_active_path.v)
in `test/tb.v` (currently it is compiled but not exercised — see the
SYNTH-1 checklist item in [`STATUS.md`](STATUS.md#immediate-checklist-what-would-move-us-up-the-ladder)).

---

## 5. What this document explicitly does **not** claim

- That φ-anchor has a complete Triple-Deck implementation. It does not.
- That FBB / RBB / CAP_BOOST have been measured on silicon. They have
  not — no φ-anchor die has been characterised.
- That the projected 22FDX numbers in `BENCHMARKS.md` apply to SKY130A.
  They do not; that section labels them "PROJECTED, 22FDX".
- That the e-engine or γ-surface dies necessarily share this exact
  rung mix. Their status lives in their own repos.

---

## 6. Cross-references

- [`STATUS.md`](STATUS.md) — readiness ladder.
- [`BENCHMARKS.md`](BENCHMARKS.md) — measured vs projected breakdown.
- [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md) — proof status for FBB.
- [`specs/fpga/fbb_active_path.t27`](specs/fpga/fbb_active_path.t27) — FBB spec.
- [`src/fbb_active_path.v`](src/fbb_active_path.v) — FBB RTL.
- [`src/avs_controller_96.v`](src/avs_controller_96.v) — AVS-96 (adjacent).
- [`src/purkinje_thermal_gate.v`](src/purkinje_thermal_gate.v) — thermal trip (adjacent).
- [`D2D_PROTOCOL.md`](D2D_PROTOCOL.md) §4.2 — "drain on restraint" interaction.
