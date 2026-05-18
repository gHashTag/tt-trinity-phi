# Issues Summary — TRI-NET 2026 (φ-anchor track)

> **All identifiers below are local plan IDs**, not GitHub issue
> numbers. GitHub numbers are minted at filing time by
> [`create_issues.sh`](create_issues.sh). The stable cross-reference
> handle is the **track ID** (`CL-01`, `EN-02`, etc.), which is what
> [`docs/SCIENTIFIC_IMPROVEMENT_PLAN.md`](../../docs/SCIENTIFIC_IMPROVEMENT_PLAN.md)
> uses.

See [`00_EPIC_2026.md`](00_EPIC_2026.md) for the epic and the global
R5-honesty framing.

## Track index

| Local ID | Track ID | Title | File | SIP § |
|---------:|----------|-------|------|------:|
| `#0`  | EPIC   | TRI-NET 2026 Scientific Improvement Plan (φ-anchor) | [`00_EPIC_2026.md`](00_EPIC_2026.md) | whole |
| `#1`  | CL-01  | D2D drain-on-restraint normative | [`01_CL-01_d2d_drain_on_restraint.md`](01_CL-01_d2d_drain_on_restraint.md) | 2 |
| `#2`  | CL-02  | Coq trace for Lucas-POST identity | [`02_CL-02_coq_lucas_post_trace.md`](02_CL-02_coq_lucas_post_trace.md) | 2 |
| `#3`  | CL-03  | Ed25519 stub spec + host verifier reference | [`03_CL-03_ed25519_stub_spec.md`](03_CL-03_ed25519_stub_spec.md) | 2 |
| `#4`  | CL-04  | Per-die anchor-mismatch flag in conformance JSON | [`04_CL-04_anchor_mismatch_flag.md`](04_CL-04_anchor_mismatch_flag.md) | 2 |
| `#5`  | EN-01  | `specs/fpga/rbb_idle_path.t27` + `cap_boost.t27` stubs | [`05_EN-01_rbb_capboost_stubs.md`](05_EN-01_rbb_capboost_stubs.md) | 3 |
| `#6`  | EN-02  | `bench/22fdx/` projection notebook | [`06_EN-02_22fdx_projection_notebook.md`](06_EN-02_22fdx_projection_notebook.md) | 3 |
| `#7`  | EN-03  | R5 gate: refuse "1000×" / "4000 TOPS/W" restatement | [`07_EN-03_refuse_ultra_headlines.md`](07_EN-03_refuse_ultra_headlines.md) | 3 |
| `#8`  | SN-01  | Ternary round-trip row in NMSE harness | [`08_SN-01_ternary_roundtrip_row.md`](08_SN-01_ternary_roundtrip_row.md) | 4 |
| `#9`  | SN-02  | Spike→D2D path documented as planned hook | [`09_SN-02_spike_d2d_hook.md`](09_SN-02_spike_d2d_hook.md) | 4 |
| `#10` | SN-03  | `tri-test.yml` SNN-burst anchor-stability job | [`10_SN-03_anchor_stability_snn_burst.md`](10_SN-03_anchor_stability_snn_burst.md) | 4 |
| `#11` | PUB-01 | Whitepaper PDF upload to existing Zenodo DOI | [`11_PUB-01_whitepaper_pdf.md`](11_PUB-01_whitepaper_pdf.md) | 5 |
| `#12` | PUB-02 | First `bench/nmse/<sha>.json` report | [`12_PUB-02_first_nmse_report.md`](12_PUB-02_first_nmse_report.md) | 5 |
| `#13` | PUB-03 | CLARA proof-trace note (blocked by CL-02) | [`13_PUB-03_clara_proof_note.md`](13_PUB-03_clara_proof_note.md) | 5 |
| `#14` | OS-01  | Preserve Apache-2.0 + open PDK posture | [`14_OS-01_apache_open_pdk_posture.md`](14_OS-01_apache_open_pdk_posture.md) | 6 |
| `#15` | OS-02  | Reference host bridge in `examples/` | [`15_OS-02_reference_host_bridge.md`](15_OS-02_reference_host_bridge.md) | 6 |
| `#16` | OS-03  | `.github/PULL_REQUEST_TEMPLATE.md` with R5 checklist | [`16_OS-03_pr_template_r5_checklist.md`](16_OS-03_pr_template_r5_checklist.md) | 6 |

## Dependencies

```
CL-02 (#2)  ──blocks──>  PUB-03 (#13)
EN-01 (#5)  ──unblocks─>  Triple-Deck RTL (out of scope; future issue)
PUB-02 (#12) ──unblocks─>  SN-01 (#8)  (NMSE harness must exist first)
EN-03 (#7) gates restatement of ultra-headline numbers
OS-01 (#14) is a standing policy anchor
```

## R5-honesty roll-up

| Category | Anti-claim enforced |
|----------|---------------------|
| Funding         | No issue asserts CLARA / programme funding (CL-01..04 are technical). |
| Silicon dates   | No issue dates silicon return. EN-02 / PUB-02 explicitly stay in projection / RTL_ONLY. |
| Paper acceptance | PUB-01..03 are draft-and-submit / deposit only. |
| Ultra-headlines | EN-03 issue actively guards against restatement. |
| DOI minting     | PUB-01 deposits a sub-record only; no new DOI. |
| Per-issue labels | Every issue body declares `track:` / `area:` / `r5:` / `type:`. |

## Filing

See [`create_issues.sh`](create_issues.sh). Default mode is **dry-run**
— it prints the `gh issue create` commands without executing them.
Pass `--apply` to execute.
