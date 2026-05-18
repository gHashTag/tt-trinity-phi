# Triple-Decker State Machine — Spec (φ-anchor view)

> **Readiness:** **SPEC (draft).** This document specifies the
> Triple-Decker power-rail state machine — `IDLE → RBB → FBB →
> CAP_BOOST → IDLE` — together with its guards, cooldown timers, and
> brownout / overcurrent fallback rules. **No RTL is committed here.**
> The matching status table for what is actually built on φ-anchor
> today lives in
> [`../TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md); only **FBB**
> is at SYNTH today, so this state machine is mostly a contract for
> future RTL.

Last updated: 2026-05-18.

Cross-refs:
[`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) ·
[`VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md) (row
`VC-DECK-4`) ·
[`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md).

---

## 1. Scope and posture

This document is the **state-machine** spec for the Triple-Decker. It
does *not* claim:

- That RBB or CAP_BOOST exist in `src/` today. They do not
  ([`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3).
- That the deck's headline TOPS/W projection has been measured.
  See [`VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md)
  rows `VC-22FDX-*` for the projection-only posture.
- That SKY130A silicon will see meaningful body-bias swing. It will
  not ([`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §2).

This document **does** specify the behaviour any future Triple-Decker
controller MUST implement to be considered TRI-NET-conformant.

---

## 2. States

| State | Meaning | Entry guard | Exit guard | Power posture |
|---|---|---|---|---|
| `IDLE`       | No deck active. Default after reset. | `rst_n=0` released; all rails nominal | activity / wake signal | nominal |
| `RBB`        | Reverse Body Bias asserted on idle blocks. | sustained idle window ≥ `T_IDLE_RBB`, no thermal trip, no brownout pending | activity detected, or thermal trip, or brownout, or cooldown override | reduced leakage; reduced clock-domain readiness |
| `FBB`        | Forward Body Bias asserted on active path. | active workload detected; `Vrail` within band; no overcurrent flag | thermal trip via Purkinje gate, overcurrent flag, brownout pending, or workload subsides for ≥ `T_FBB_DRAIN` | increased speed at low V; higher leakage; controlled |
| `CAP_BOOST`  | Decap-assisted rail boost asserted for burst headroom. | FBB active **and** `burst_request=1` **and** `cap_boost_armed=1` (reservoir cap charged) **and** `T_BOOST_COOLDOWN` elapsed since previous boost | `T_BOOST_MAX` elapsed (mandatory drop), burst_request deasserted, droop detector trips, or brownout pending | brief Vrail headroom; rapid reservoir drain |
| `BROWNOUT`   | Safety state: all decks released, Vrail below safe threshold. | `Vrail < V_BROWNOUT_LOW` for ≥ `T_BROWNOUT_CONFIRM` cycles, OR overcurrent flag latched | `Vrail > V_BROWNOUT_CLEAR` for ≥ `T_BROWNOUT_CLEAR` cycles AND overcurrent flag clear | minimum-safe; deck outputs forced 0 |

`BROWNOUT` is the **fallback sink** — every other state MUST be able to
reach it within one decision cycle on a brownout-pending condition.

---

## 3. Canonical transition diagram

```
                  +-----------+
                  |   IDLE    |
                  +-----+-----+
                        |
        idle ≥ T_IDLE_RBB |  ^ wake / activity
                        v  |
                  +-----+-----+
       wake -----►|    RBB    |
                  +-----+-----+
                        |
       activity & Vrail OK | ^ workload subsides ≥ T_FBB_DRAIN
                        v  |
                  +-----+-----+
                  |    FBB    |
                  +-----+-----+
                        |
   burst_request=1 &    | ^ T_BOOST_MAX elapsed
   cap_boost_armed=1 &  | | OR burst done
   T_BOOST_COOLDOWN ok  | | OR droop trip
                        v |
                  +-----+-----+
                  | CAP_BOOST |
                  +-----+-----+
                        |
                        v
                       IDLE
```

Brownout fallback (from any state):

```
              +---------------------------+
              | Vrail<V_BROWNOUT_LOW or   |
              | overcurrent_flag latched  |
              +-------------+-------------+
                            v
                       +---------+
                       | BROWNOUT|
                       +----+----+
                            | Vrail recovers
                            v
                          IDLE
```

The progression `IDLE → RBB → FBB → CAP_BOOST → IDLE` named in row
`VC-DECK-4` of the claims matrix is the **principal loop**. The
brownout transition is an unconditional override that may pre-empt
*any* state in that loop within one decision cycle.

---

## 4. Guards (normative)

| Guard | Symbol | Type | Notes |
|---|---|---|---|
| Idle window before RBB                          | `T_IDLE_RBB`           | cycle counter | tunable; default placeholder = 1024 cycles. |
| FBB active-path armed                           | `fbb_arm`              | level         | from workload monitor; gated by `purkinje_thermal_gate`. |
| FBB drain hold-down                             | `T_FBB_DRAIN`          | cycle counter | minimum time FBB stays asserted after workload subsides; default placeholder = 64 cycles. |
| CAP_BOOST armed (reservoir-cap charged)         | `cap_boost_armed`      | level         | from analog/digital monitor; absent in SKY130A. |
| CAP_BOOST max-on time                           | `T_BOOST_MAX`          | cycle counter | mandatory drop; default placeholder = 32 cycles. |
| Cooldown between CAP_BOOST asserts              | `T_BOOST_COOLDOWN`     | cycle counter | enforces minimum spacing between boosts; default placeholder = 256 cycles. |
| Thermal trip                                    | `purkinje_trip`        | edge          | latched at `purkinje_thermal_gate` ([`src/purkinje_thermal_gate.v`](../src/purkinje_thermal_gate.v)); forces FBB→IDLE and disarms CAP_BOOST. |
| Overcurrent flag                                | `overcurrent_flag`     | latch         | from AVS-96 sense path ([`src/avs_controller_96.v`](../src/avs_controller_96.v)); BROWNOUT immediately. |
| Brownout confirm window                         | `T_BROWNOUT_CONFIRM`   | cycle counter | required cycles of `Vrail<V_BROWNOUT_LOW` before declaring BROWNOUT; default = 8. |
| Brownout clear window                           | `T_BROWNOUT_CLEAR`     | cycle counter | required cycles of `Vrail>V_BROWNOUT_CLEAR` before leaving BROWNOUT; default = 16. |

All numeric defaults are **placeholders** for the spec gate to
recognise; a future RTL PR is expected to land calibrated values.

---

## 5. Priority and pre-emption

Decision order, top to bottom (highest priority wins):

1. `overcurrent_flag` latched ⇒ **BROWNOUT** (one cycle).
2. `Vrail` below `V_BROWNOUT_LOW` for `T_BROWNOUT_CONFIRM` cycles ⇒ **BROWNOUT**.
3. `purkinje_trip` ⇒ exit FBB and CAP_BOOST to IDLE; rearm requires
   `purkinje_trip` deasserted + cooldown.
4. CAP_BOOST guards (max-on, cooldown).
5. FBB drain hold-down.
6. RBB idle-window entry.

This order is normative; an implementation that flips priorities
between rules 1 and 2 is non-conformant because the latched flag is
the deterministic signal.

---

## 6. Cooldown rules

- **CAP_BOOST cooldown** (`T_BOOST_COOLDOWN`) MUST elapse between
  successive `IDLE/FBB → CAP_BOOST` transitions, even if
  `burst_request` re-asserts immediately. Rationale: prevents reservoir
  thrash and rail droop.
- **FBB drain hold-down** (`T_FBB_DRAIN`) prevents thrash between
  FBB and IDLE on bursty workloads.
- **Brownout sticky** — once entered, BROWNOUT can only be left after
  `T_BROWNOUT_CLEAR` AND `overcurrent_flag=0`. A counter MUST NOT be
  reset by a transient.

---

## 7. Brownout / overcurrent fallback

| Condition | Source | Required reaction |
|---|---|---|
| `Vrail < V_BROWNOUT_LOW` for `T_BROWNOUT_CONFIRM` cycles | AVS-96 sense path | Force IDLE, then BROWNOUT in the next decision cycle. All deck outputs MUST be driven inactive within 1 cycle. |
| `overcurrent_flag` latched   | AVS-96 / external sense | Same as above; latch is sticky until clear. |
| `purkinje_trip` (thermal)    | `purkinje_thermal_gate.v` | Exit FBB and CAP_BOOST to IDLE; do NOT enter BROWNOUT unless an additional overcurrent / brownout flag fires. |

The state machine MUST treat brownout as a **single-cycle** override —
any non-IDLE state transitions to BROWNOUT on the next clock edge once
the entry guard is satisfied.

---

## 8. Observability requirements

A conformant implementation MUST expose, at minimum, the following
status bits to a `restraint_ctrl` consumer
([`src/restraint_ctrl.v`](../src/restraint_ctrl.v)):

| Bit | Meaning |
|---|---|
| `deck_state[2:0]`     | current state encoding (IDLE=0, RBB=1, FBB=2, CAP_BOOST=3, BROWNOUT=4). |
| `deck_brownout`       | sticky brownout flag; cleared only by restraint_ctrl. |
| `deck_overcurrent`    | sticky overcurrent flag. |
| `deck_thermal_trip`   | sticky thermal-trip flag. |
| `deck_boost_count[N]` | rolling count of CAP_BOOST asserts, for telemetry. |

These bits are *spec-level* names; the bit positions become normative
when a `src/triple_decker_ctrl.v` lands.

---

## 9. R5 honesty notes

- No measured rail trace, no measured leakage delta, and no measured
  burst recovery time is asserted by this spec. All timing constants
  are placeholders to be calibrated post-fab.
- The state machine is the *contract*. It does NOT imply any deck
  will operate at SKY130A; per
  [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §2, body-bias
  swing is limited at 130 nm.
- The brownout reaction MUST NOT be skipped, fast-pathed, or
  "optimised" by an implementation: it is a safety state, and any
  re-ordering is a conformance violation.

---

## 10. Acceptance criteria for the matching RTL PR

Before any `src/triple_decker_ctrl.v` is merged:

1. Add `specs/fpga/triple_decker_ctrl.t27` with calibrated values for
   every guard in §4.
2. Add a `test/tb_triple_decker.v` (or cocotb job) that exercises:
   the principal loop, the brownout override from each state, the
   cooldown enforcement, and the thermal-trip pre-emption.
3. Add a row to [`VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md)
   per measured behaviour; flip `VC-DECK-2` and `VC-DECK-3` away from
   `NOT MEASURED` only when the RTL exists.
4. Preserve R-SI-1: no `*` operators introduced.
5. Update [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3 in
   the same PR.
