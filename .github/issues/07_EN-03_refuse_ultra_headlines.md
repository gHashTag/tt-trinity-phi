# [EN-03] R5-honesty gate — refuse "1000×" / "4000 TOPS/W" restatement

**Local plan ID:** `#7` (placeholder).
**Track:** EN-03.
**SIP section:** §3.
**Labels:** `track:EN`, `area:honesty`, `r5:target`, `type:ci`.

## Goal (target)

Add a CI / repo-side gate that forbids restating ultra-headline
efficiency numbers (e.g. "1000×", "4000 TOPS/W") as facts. Such
numbers, if cited from external press, remain external and labelled
`VERIFY`.

## Scope

- Add a small `tools/check_no_ultra_claims.sh` (or extend an existing
  R-SI workflow) that fails CI on `1000x|1000×|4000\s*TOPS` outside
  of `VERIFY:` / "external press" contexts.
- Allow-list any current references that are already gated by an
  external citation.

## Done when

- [ ] Gate runs on every PR.
- [ ] No new violation introduced.
- [ ] Existing repo passes the check.

## Anti-claims

- This is a guard, not a comment on the truth-value of the external numbers.
- The gate fires on **restatement-as-fact**, not on quoting + `VERIFY` framing.
