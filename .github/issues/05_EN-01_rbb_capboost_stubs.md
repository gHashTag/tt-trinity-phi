# [EN-01] `specs/fpga/rbb_idle_path.t27` + `cap_boost.t27` stubs

**Local plan ID:** `#5` (placeholder).
**Track:** EN-01.
**SIP section:** §3.
**Labels:** `track:EN`, `area:power`, `r5:target`, `type:spec`.

## Goal (target)

Land `.t27` SPEC stubs for **RBB** (Reverse Body Bias) and
**CAP_BOOST** (decap-assisted rail boost) following the convention of
[`specs/fpga/fbb_active_path.t27`](../../specs/fpga/fbb_active_path.t27).

Per [`TRIPLE_DECK_STATUS.md`](../../TRIPLE_DECK_STATUS.md) §3, only
FBB has RTL on φ-anchor today; this issue does **not** add the RTL —
it adds the SPEC step that must precede it.

## Scope

- `specs/fpga/rbb_idle_path.t27` (opcode, idle-detect, Vth bump, re-entry latency).
- `specs/fpga/cap_boost.t27` (burst trigger, reservoir-cap parameters — architectural only, SKY130A cannot host the real cap).
- Cross-link from [`TRIPLE_DECK_STATUS.md`](../../TRIPLE_DECK_STATUS.md) §4.1 / §4.2.

## Done when

- [ ] Both `.t27` files land and are referenced from the status doc.
- [ ] `SPEC-DECK-1` checkbox closed in [`STATUS.md`](../../STATUS.md).
- [ ] No RTL added under `src/` in this issue.

## Anti-claims

- No measured leakage / burst data.
- CAP_BOOST is fundamentally an analog/process feature; the digital
  RTL would only be the controller.
