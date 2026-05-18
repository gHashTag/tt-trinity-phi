# [CL-02] Coq trace for Lucas-POST identity

**Local plan ID:** `#2` (placeholder).
**Track:** CL-02.
**SIP section:** §2.
**Labels:** `track:CL`, `area:proof`, `r5:target`, `type:proof`.

## Goal (target)

Land at least one machine-checked Coq / Rocq proof for the Lucas POST
identity `φ² + φ⁻² = L₂ = 3`, referenced from `coq/` or `trios-coq/`.

## Scope

- Add a `.v` file under `coq/` (or `trios-coq/`) whose statement is
  the Lucas L₂ identity used by [`src/phi_anchor_post.v`](../../src/phi_anchor_post.v).
- Update [`CLARA_PROOF_MANIFEST.md`](../../docs/CLARA_PROOF_MANIFEST.md) to cite the proof.
- Update [`CLARA_TRACEABILITY.md`](../../CLARA_TRACEABILITY.md) traceability row from "sketch" to "machine-checked".

## Done when

- [ ] `.v` proof file compiles with the project's Coq toolchain.
- [ ] Manifest cites the file + commit SHA.
- [ ] PUB-03 (proof-trace note) becomes unblocked.

## Anti-claims

- "Machine-checked" applies to the listed identity only — not to the
  entire φ-anchor design.
- No claim of CLARA proof-portfolio acceptance.
