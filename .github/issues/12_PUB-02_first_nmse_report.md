# [PUB-02] First `bench/nmse/<sha>.json` report

**Local plan ID:** `#12` (placeholder).
**Track:** PUB-02.
**SIP section:** §5.
**Labels:** `track:PUB`, `area:bench`, `r5:target`, `type:bench`.

## Goal (target)

Land the harness contracted by [`GF16_BFLOAT16_NMSE.md`](../../GF16_BFLOAT16_NMSE.md)
and emit a first report under `bench/nmse/<sha>.json`.

## Scope

- `tools/nmse_gf16_bf16.py` host harness covering D-1..D-6.
- First `bench/nmse/<git_sha>.json` report in `RTL_ONLY` mode (no
  silicon yet).
- CI smoke that runs the harness on every push (optional gating).

## Done when

- [ ] Report file lands.
- [ ] `SPEC-NMSE-1` checkbox closed in [`STATUS.md`](../../STATUS.md).
- [ ] No `Δ_dB` number anywhere in narrative prose before the report exists.

## Anti-claims

- `RTL_ONLY` provenance, not measured silicon.
- The report **is** the claim — no out-of-band number quoting.
