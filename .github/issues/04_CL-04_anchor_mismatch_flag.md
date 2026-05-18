# [CL-04] Per-die anchor-mismatch flag in conformance JSON

**Local plan ID:** `#4` (placeholder).
**Track:** CL-04.
**SIP section:** §2.
**Labels:** `track:CL`, `area:conformance`, `r5:target`, `type:ci`.

## Goal (target)

Extend [`.github/workflows/tri-test.yml`](../../.github/workflows/tri-test.yml)
output so anchor-parity failures emit a per-die flag in the
conformance JSON ([`conformance/FORMAT-SPEC-001.json`](../../conformance/FORMAT-SPEC-001.json)
or sibling). No behaviour change on φ-anchor.

## Scope

- Define the JSON delta in [`conformance/`](../../conformance/) (additive only).
- Update `tri-test.yml` to emit the flag.
- Update [`D2D_PROTOCOL.md`](../../D2D_PROTOCOL.md) §5 acceptance bullet (5) to reference the flag.

## Done when

- [ ] JSON schema delta committed.
- [ ] CI emits the flag and surfaces it on failure.
- [ ] No false positives on the canonical `0x47C0` path.

## Anti-claims

- No silicon claim.
- The flag reflects CI / SIM state only, not measured die behaviour.
