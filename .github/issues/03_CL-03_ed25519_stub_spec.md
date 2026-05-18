# [CL-03] Ed25519 stub spec + host verifier reference

**Local plan ID:** `#3` (placeholder).
**Track:** CL-03.
**SIP section:** §2.
**Labels:** `track:CL`, `area:provenance`, `r5:target`, `type:spec`.

## Goal (target)

Author an Ed25519 signing-path spec stub plus a host-side verifier
reference, so the provenance receipt chain in
[`D2D_PROTOCOL.md`](../../D2D_PROTOCOL.md) §2 (anchor word + HWRNG
nonce + Lucas-POST sticky bit) can be signed off-chip.

## Scope

- Add `specs/crypto/ed25519_phi.t27` (stub) describing the signing
  surface — input fields, key derivation, output format.
- Add a `tools/verify_phi_receipt.py` reference verifier (host-side
  Python), used only by CI smoke and integrators.
- Update [`docs/PHI_ED25519_ROADMAP.md`](../../docs/PHI_ED25519_ROADMAP.md)
  to point at the spec.

## Done when

- [ ] Spec stub lands and is linked from the roadmap doc.
- [ ] Host-side verifier round-trips a synthetic receipt in CI.
- [ ] No on-die RTL is added in this issue (would be a separate PR).

## Anti-claims

- No on-die signing implemented in this issue.
- No claim of FIPS / formal compliance.
