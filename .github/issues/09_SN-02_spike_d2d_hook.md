# [SN-02] Spike→D2D path documented as planned hook

**Local plan ID:** `#9` (placeholder).
**Track:** SN-02.
**SIP section:** §4.
**Labels:** `track:SN`, `area:d2d`, `r5:target`, `type:docs`.

## Goal (target)

Document the **spike → D2D** path on the φ-anchor side as a *planned*
hook in [`D2D_PROTOCOL.md`](../../D2D_PROTOCOL.md) §4, contingent on
the γ-surface track opening this surface.

## Scope

- A new bullet in `D2D_PROTOCOL.md` §4 listing spike-event ingestion
  as planned, with no RTL claim.
- Sibling note in [`docs/SCIENTIFIC_IMPROVEMENT_PLAN.md`](../../docs/SCIENTIFIC_IMPROVEMENT_PLAN.md) §4 SN-02 row.
- Pointer to the γ-surface repo (`tt-trinity-gamma`) as the upstream owner.

## Done when

- [ ] Doc updated; no behaviour change.
- [ ] γ-surface repo confirms a matching hook is on its roadmap.

## Anti-claims

- φ-anchor is the master gate, not a spike datapath; this issue does **not**
  promise SNN routing on the φ die.
