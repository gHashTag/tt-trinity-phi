# [SN-03] `tri-test.yml` SNN-burst anchor-stability job

**Local plan ID:** `#10` (placeholder).
**Track:** SN-03.
**SIP section:** §4.
**Labels:** `track:SN`, `area:conformance`, `r5:target`, `type:ci`.

## Goal (target)

Add a job to [`.github/workflows/tri-test.yml`](../../.github/workflows/tri-test.yml)
that drives SNN-like traffic on the fabric and re-asserts that the
canonical `0x47C0` anchor remains stable on φ-anchor.

## Scope

- New job (or step) that injects a parameterised burst.
- Assertion: `{uio_out, uo_out} == 0x47C0` after every burst window.

## Done when

- [ ] Job green on default config.
- [ ] Assertion fires on intentional violation (negative test).

## Anti-claims

- Tests SIM anchor stability, not silicon.
- Does not measure SNN throughput.
