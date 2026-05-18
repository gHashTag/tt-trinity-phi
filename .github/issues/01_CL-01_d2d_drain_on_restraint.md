# [CL-01] D2D drain-on-restraint normative

**Local plan ID:** `#1` (placeholder; GitHub issue number minted by `create_issues.sh`).
**Track:** CL-01 (DARPA CLARA alignment — restraint kill-switch).
**SIP section:** [`docs/SCIENTIFIC_IMPROVEMENT_PLAN.md`](../../docs/SCIENTIFIC_IMPROVEMENT_PLAN.md) §2.
**Labels:** `track:CL`, `area:d2d`, `r5:target`, `type:spec`.

## Goal (target)

Promote the "drain on restraint" semantic from a SPEC stub in
[`D2D_PROTOCOL.md`](../../D2D_PROTOCOL.md) §4.2 to a normative section
of a v1.1 sibling of
[`docs/INTERCONNECT_PROTOCOL_V1.md`](../../docs/INTERCONNECT_PROTOCOL_V1.md).

## Scope

- Add a v1.1 spec section: when any TRI-NET die asserts
  `restraint_mode`, the fabric MUST drain all in-flight frames before
  re-enabling traffic.
- Add a cocotb test under `test/` that exercises restraint→drain on
  the φ-anchor side.
- Update [`D2D_PROTOCOL.md`](../../D2D_PROTOCOL.md) §4.2 to point at
  the new normative section instead of describing the semantic
  inline.

## Done when

- [ ] Spec section landed (v1.1 file or §X of v1.0).
- [ ] cocotb test passes locally and on CI.
- [ ] `SPEC-D2D-1` checkbox closed in [`STATUS.md`](../../STATUS.md).

## Anti-claims

- No silicon claim. SIM rung only.
- No assertion that any external programme (CLARA) has funded this.
