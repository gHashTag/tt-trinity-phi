# D2D Conformance Vectors — TRI-NET / TTSKY26b

> **Readiness:** **SPEC / CONFORMANCE.** The JSON vectors in this
> directory describe expected wire-level behaviour of the TRI-NET D2D
> (die-to-die) interconnect, as pinned by
> [`../../docs/INTERCONNECT_PROTOCOL_V1.md`](../../docs/INTERCONNECT_PROTOCOL_V1.md)
> and the φ-anchor role layer in
> [`../../D2D_PROTOCOL.md`](../../D2D_PROTOCOL.md). They are
> reference traces that any compatible bridge MUST reproduce.

Last updated: 2026-05-18.

---

## What is in this directory

| File | Scenario | Claims matrix row |
|---|---|---|
| [`valid_header.json`](valid_header.json)           | Valid `ANCHOR` (TYPE=0x47) frame with correct CRC; slave asserts ACK within budget. | VC-D2D-1, VC-D2D-3, VC-ANCHOR-3 |
| [`bad_crc.json`](bad_crc.json)                     | Identical frame with intentionally corrupted CRC; slave MUST NOT ACK and MUST drop the frame before any state change. Phi retries with correct CRC. | VC-D2D-3 |
| [`unsupported_opcode.json`](unsupported_opcode.json) | TYPE byte outside `{0x47, 0x93, 0xE0, 0xC1}`; slaves drop silently, increment `err_cnt`, no ACK. | VC-D2D-3 |
| [`timeout_retry.json`](timeout_retry.json)         | Valid frame to a non-responding slave; Phi exhausts the retry budget (3 retries → RESYNC). | VC-D2D-3 |
| [`multi_chip_ordering.json`](multi_chip_ordering.json) | Two-slave (Euler + Gamma) ordering: wired-AND ACK is observed low only when **all** addressed slaves have asserted; Phi reads ACK-complete only when Wire C returns high. | VC-D2D-3, VC-D2D-4 |

These cover all five conformance scenarios required by
[`docs/VERIFICATION_CLAIMS_MATRIX.md`](../../docs/VERIFICATION_CLAIMS_MATRIX.md)
row `VC-D2D-3`.

---

## Schema

Each file shares a common envelope (see `valid_header.json` for the
canonical example):

```jsonc
{
  "$schema": "tt-trinity-phi/d2d-conformance-vector/1.0",
  "scenario_id":    "D2D-VEC-<n>",
  "scenario_name":  "<human-readable>",
  "claims_matrix_rows": ["VC-D2D-..."],
  "protocol_version":   "1.0",
  "protocol_ref":       "docs/INTERCONNECT_PROTOCOL_V1.md",
  "expected_outcome":   "ack_within_budget | drop_and_retry | drop_silent | resync_after_retries | wired_and_ack_complete",
  "frames": [
    {
      "direction":  "phi_to_slaves | slave_to_phi",
      "type_byte":  "0x47",
      "len":        4,
      "payload":    ["0x02", "0x03", "0x04", "0x07"],
      "crc8":       "0xAB",
      "crc_valid":  true,
      "eof_marker": "ui_in[0]=0 for 2 cycles"
    }
  ],
  "wire_trace": [
    { "cycle": 0, "wire_a_load_mode": 1, "wire_b_sync_strobe": 0, "wire_c_ack": "Hi-Z (pulled high)" }
  ],
  "expected_state_transitions": ["IDLE", "LOAD_PHASE", "SYNC_BURST", "IDLE"],
  "expected_counters": { "err_cnt_delta": 0, "retry_cnt_delta": 0 },
  "anti_claim": "What would make this vector wrong."
}
```

The `wire_trace` array is a normalised, cycle-numbered snapshot, not
a full GTKWave VCD — it is a *spec*-grade trace meant for diff-based
checks. A real harness translates it to a per-clock-edge expectation.

---

## R5 honesty posture

- These vectors are derived from the **frozen** TIP v1.0 spec, not from
  a silicon capture. There is no measured-die data in this directory.
- A vector whose `crc8` field disagrees with the §5.4 algorithm is a
  spec bug — fix the vector, do not change the algorithm.
- The protocol version is `1.0` and matches the version field policy
  in [`docs/INTERCONNECT_PROTOCOL_V1.md`](../../docs/INTERCONNECT_PROTOCOL_V1.md) §1.3.

---

## Verification

The spec gate
[`../../scripts/check_trinet_specs.sh`](../../scripts/check_trinet_specs.sh)
verifies, for each file:

1. JSON parses cleanly.
2. Required fields exist (`scenario_id`, `frames`, `expected_outcome`,
   `claims_matrix_rows`).
3. Every `claims_matrix_rows` entry is present in
   [`docs/VERIFICATION_CLAIMS_MATRIX.md`](../../docs/VERIFICATION_CLAIMS_MATRIX.md).
4. The full set of required scenarios (valid header / bad CRC /
   unsupported opcode / timeout-retry / multi-chip ordering) is
   present.
