# [OS-01] Preserve Apache-2.0 + open PDK posture (no relicense)

**Local plan ID:** `#14` (placeholder).
**Track:** OS-01.
**SIP section:** §6.
**Labels:** `track:OS`, `area:license`, `r5:target`, `type:policy`.

## Goal (preserve)

Keep Apache-2.0 with no field-of-endeavor restriction and keep the
SKY130A flow as the default in [`.github/workflows/gds.yaml`](../../.github/workflows/gds.yaml).

## Scope

- No code change. This issue exists to make the policy explicit and
  to gate any future PR that would alter it.
- A PR that touches [`LICENSE`](../../LICENSE) or the SKY130A flow
  config must reference this issue and explain the deviation.

## Done when

- [ ] Issue stays open as a policy anchor for the duration of the line.

## Anti-claims

- No third-party attestation of license / posture.
- No promise of perpetuity beyond what Apache-2.0 itself provides.
