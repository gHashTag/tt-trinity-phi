# TRI-NET 2026 Scientific Improvement Plan — φ-anchor view

> **Readiness:** **PLAN ONLY.** This document is the φ-anchor-side
> adaptation of the line-level TRI-NET 2026 Scientific Improvement
> Plan. Every figure that has not been measured *in this repo* or
> cited from an external source is marked one of:
>
> - `VERIFY` — claim referenced from outside this repo; integrator
>   must verify the source before quoting it.
> - `projection` — architecture-level estimate, not silicon.
> - `target` — programmatic goal, not an achieved outcome.
>
> No measured silicon, no funded-program facts, no accepted-paper
> claims, no DOI minted by this PR. The existing TRI-NET DOI
> `10.5281/zenodo.19227877` is the only DOI quoted here, and it is
> already anchored to the TTSKY26b shuttle commit (see
> [`CHANGELOG.md`](../CHANGELOG.md)).

Last updated: 2026-05-18. Owner: φ-anchor track.

---

## 0. How this document fits with the rest of the repo

| Concern | Authoritative file |
|---------|--------------------|
| Readiness ladder              | [`STATUS.md`](../STATUS.md) |
| Measured vs projected         | [`BENCHMARKS.md`](../BENCHMARKS.md) |
| Line-level positioning        | [`LINEUP.md`](../LINEUP.md) |
| Peer-chip framing             | [`COMPETITORS.md`](../COMPETITORS.md) |
| Assurance / proof evidence    | [`CLARA_TRACEABILITY.md`](../CLARA_TRACEABILITY.md), [`CLARA_PROOF_MANIFEST.md`](CLARA_PROOF_MANIFEST.md) |
| D2D / chip-to-chip role       | [`../D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) |
| GF16 vs bf16 NMSE             | [`../GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) |
| RBB / FBB / CAP_BOOST status  | [`../TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) |
| 22FDX TOPS/W projection       | [`../TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) |
| External-integration API      | [`../TRI_NET_API.md`](../TRI_NET_API.md) |
| Whitepaper hub                | [`../WHITEPAPER.md`](../WHITEPAPER.md) |

This plan is the **narrative roadmap**; the linked files are the
**evidence layer**. If they disagree, the evidence layer wins.

---

## 1. φ-anchor's current state (in two lines)

- **Implemented today.** Canonical `0x47C0` anchor at SYNTH / GDS, Lucas
  L₂..L₇ POST (`φ² + φ⁻² = 3`), HWRNG nonce, friend/foe handshake,
  CLARA Gap-4 `restraint_ctrl`, GF4..GF256 + quantizer + power-module
  RTL (`info.yaml`), Trinity Interconnect Protocol v1.0 (frozen at
  TTSKY26b).
- **Not implemented today.** Holographic-routing D2D extensions
  (`D2D_PROTOCOL.md` §4), NMSE harness, RBB and CAP_BOOST decks
  (`TRIPLE_DECK_STATUS.md` §3 — only FBB is in RTL), 22FDX synthesis
  (`TOPS_W_22FDX_PROJECTION.md` §3).

The plan below moves the second list toward the first **without
inventing intermediate facts**.

---

## 2. DARPA CLARA alignment — CL-01..CL-04

The DARPA CLARA programme description is referenced from
[`docs/TRI_NET_DARPA_CLARA_PROPOSAL.md`](TRI_NET_DARPA_CLARA_PROPOSAL.md)
and the public CLARA page (`VERIFY` against
<https://www.darpa.mil/research/programs/clara>). No funding,
contract status, or programme date is asserted here.

| ID | Item | Track | Today | 2026 target |
|----|------|-------|-------|-------------|
| **CL-01** | Restraint-controller protocol-level kill-switch wired through D2D so any TRI-NET die that trips `restraint_mode` drains the fabric. | φ-anchor (control endpoint) | `restraint_ctrl.v` at SYNTH; D2D drain semantic is **planned**, see [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §4.2. | Promote D2D drain semantic from SPEC stub to v1.1 normative; cocotb test for restraint→drain. **target** |
| **CL-02** | Coq / Rocq proof index for CLARA gaps reachable from φ-anchor. | φ-anchor (provenance endpoint) | Gap-4 sketched. Proof manifest in [`CLARA_PROOF_MANIFEST.md`](CLARA_PROOF_MANIFEST.md). Other gaps **not** claimed on φ — see README "Note: φ-anchor validates the base arithmetic layer". | Land at least one machine-checked Coq proof referenced from `coq/` / `trios-coq/` for the Lucas POST identity. **target** |
| **CL-03** | Provenance receipt chain: anchor word + HWRNG nonce + Lucas-POST sticky bit signed off-chip. | φ-anchor + host bridge | All three signals exist on-die; signing path is planned only ([`PHI_ED25519_ROADMAP.md`](PHI_ED25519_ROADMAP.md)). | Land an Ed25519 stub spec under `specs/` plus a host-side verifier reference. **target** |
| **CL-04** | Cross-die anchor (`0x47C0` TG-TRIAD-X) audited on every shuttle. | line-level / φ-anchor leads | CI: [`.github/workflows/tri-test.yml`](../.github/workflows/tri-test.yml) checks anchor parity. | Extend to a per-die anchor-mismatch flag in the conformance JSON; no behaviour change in φ. **target** |

R5-honest gates on this row: no claim is made that CLARA has funded
this work; no programme date is named.

---

## 3. Energy efficiency — EN-01..EN-03

Numbers in this section are all `projection` or `target`. The
**measured** column always cites `BENCHMARKS.md` rather than restating
a number, so it cannot drift.

| ID | Item | Today (φ-anchor) | 2026 target |
|----|------|------------------|-------------|
| **EN-01** | Triple-Deck (RBB → FBB → CAP_BOOST) on φ-anchor. | **Only FBB** is in RTL today (`src/fbb_active_path.v` at SYNTH). RBB and CAP_BOOST are explicitly not implemented — see [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3. | Land `specs/fpga/rbb_idle_path.t27` and `specs/fpga/cap_boost.t27` stubs, then RTL skeletons. SIM exercises in `test/tb.v`. No silicon claim. **target** |
| **EN-02** | TOPS/W envelope at 22FDX. | Projected **28–120 TOPS/W** (architecture-level, `projection`) — see [`BENCHMARKS.md`](../BENCHMARKS.md#architecture-projections-projected-from-rtl-intent-only) and [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md). The figure is `peer-review pending` per README. SKY130A demonstrator is not characterised on silicon. | Author the `bench/22fdx/` notebook called for by `TOPS_W_22FDX_PROJECTION.md` §4 so the projection becomes reproducible from `BENCHMARKS.md` cell-count table. **target** |
| **EN-03** | Ultra-headline figures (e.g. "1000× efficiency", "4000 TOPS/W"). | **Not claimed** anywhere in this repo. Such numbers, if cited from external press, are flagged `VERIFY` and remain external. | Continue to refuse any in-repo restatement until measured-silicon data is in `BENCHMARKS.md` MEASURED rows. **R5-honest target.** |

EN-03 is deliberately conservative: the headline figures in some
TRI-NET press material are not in this repo and **MUST NOT** be
quoted as facts by code review of this PR.

---

## 4. SNN-TRI fusion — SN-01..SN-03

φ-anchor is **not** a spiking-neural-network surface — that role is on
γ-surface ([`LINEUP.md`](../LINEUP.md)). Items here are the φ-side hooks.

| ID | Item | φ-anchor role | 2026 target |
|----|------|---------------|-------------|
| **SN-01** | Ternary {-1, 0, +1} substrate shared with SNN datapaths. | Already in numeric registry — see [`specs/numeric/formats.t27`](../specs/numeric/formats.t27) `ternary` and [`docs/TRI_NET_FORMATS_SUMMARY.md`](TRI_NET_FORMATS_SUMMARY.md). | Add `ternary` round-trip row to the NMSE harness once it lands (see [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md) §3 D-1..D-6). **target** |
| **SN-02** | Spike-event ingestion into the φ-anchor master. | Out of scope on φ-anchor: master gate only. Any spike fusion happens via D2D from γ-surface. | Document the spike→D2D path as a *planned* hook in [`D2D_PROTOCOL.md`](../D2D_PROTOCOL.md) §4 if a γ-side PR opens this surface. **target** |
| **SN-03** | Anchor-word stability under SNN burst load. | The 0x47C0 anchor is combinational and `load_mode=0` — it is unaffected by SNN packets, by construction. | Add a `tri-test.yml` job that drives SNN-like traffic on the fabric and re-asserts 0x47C0 stability. **target** |

No paper, no programme, and no benchmark figure is claimed here.

---

## 5. Publication path — PUB-01..PUB-03

This section is **planning of writing**, not announcement of
acceptance. No venue is claimed as accepting any TRI-NET work.

| ID | Item | Status | 2026 target |
|----|------|--------|-------------|
| **PUB-01** | TRI-NET line whitepaper (PDF, consolidated). | Hub exists ([`WHITEPAPER.md`](../WHITEPAPER.md)); PDF **not yet uploaded** to Zenodo (`TOPS_W_22FDX_PROJECTION.md` §4 row). | Produce a PDF that cites only `BENCHMARKS.md` MEASURED rows; upload as a new sub-record under DOI `10.5281/zenodo.19227877`. **target** |
| **PUB-02** | NMSE GF16 vs bfloat16 measurement note. | Protocol drafted in [`GF16_BFLOAT16_NMSE.md`](../GF16_BFLOAT16_NMSE.md); **no report in `bench/nmse/`**. | Land the harness, emit a first `bench/nmse/<sha>.json`, then write the note. No `Δ_dB` number anywhere in repo until then. **target** |
| **PUB-03** | CLARA proof-trace note. | Proof manifest exists ([`CLARA_PROOF_MANIFEST.md`](CLARA_PROOF_MANIFEST.md)); machine-checked Coq still partial. | When CL-02 closes, write a short note citing the green Coq trace from `coq/` and `trios-coq/`. **target** |

No venue (workshop, conference, journal) is named as accepting any of
the above. The plan is to **draft and submit** — anything beyond is
`VERIFY`.

---

## 6. Open-source community — OS-01..OS-03

| ID | Item | Status | 2026 target |
|----|------|--------|-------------|
| **OS-01** | Apache-2.0 + open PDK posture. | Already in [`LICENSE`](../LICENSE); SKY130A flow in [`.github/workflows/gds.yaml`](../.github/workflows/gds.yaml). | Keep: no field-of-endeavor restriction, no relicense. **target (= preserve current state)** |
| **OS-02** | External-integration surface. | [`TRI_NET_API.md`](../TRI_NET_API.md) ships in this PR; pin-level API frozen ([`API.md`](API.md), [`PINOUT.md`](PINOUT.md)). | Add a reference host-bridge in `examples/` once a TTSKY26b die is in hand. **target** |
| **OS-03** | Issue / PR hygiene + CLA. | No CLA today; PR template not present. | Add a `.github/PULL_REQUEST_TEMPLATE.md` whose checklist enforces the R5 framing (no measured-silicon claim without `BENCHMARKS.md` row). **target** |

OS-03 is the most under-served item; OS-01 is the most stable.

---

## 7. Timeline

| Quarter (2026, `target`) | φ-anchor milestone | Linked items |
|--------------------------|--------------------|--------------|
| Q2 2026 | Spec stubs (this PR) land on `main`. PR template lands (OS-03). | OS-03, this PR. |
| Q3 2026 | NMSE harness `tools/nmse_gf16_bf16.py` lands; first `bench/nmse/` JSON. SPEC-NMSE-1 closes in `STATUS.md`. | PUB-02, EN-02, SN-01. |
| Q3 2026 | `specs/fpga/rbb_idle_path.t27` + `specs/fpga/cap_boost.t27` stubs. SPEC-DECK-1 closes. | EN-01, CL-01. |
| Q4 2026 | `bench/22fdx/` projection notebook; reproducible 28–120 TOPS/W band. SPEC-22FDX-1 closes. | EN-02. |
| Q4 2026 | First Coq trace for Lucas-POST identity (CL-02). | CL-02, PUB-03. |
| open | Whitepaper PDF upload to Zenodo (PUB-01). | PUB-01. |
| open | TTSKY26b silicon arrival + characterisation. | converts EN-02 from `projection` to MEASURED. |

The "open" rows are deliberately undated: silicon return and PDF
publication depend on external timelines this repo does not control,
so they get no `target` date.

---

## 8. Success metrics (φ-anchor side)

A metric is "successful" only when it is verifiable from the repo or
from an external resource that this repo cites. Otherwise it stays
`target`.

| Metric | Source of truth | Pass condition |
|--------|-----------------|----------------|
| Anchor parity 0x47C0          | [`.github/workflows/tri-test.yml`](../.github/workflows/tri-test.yml) | Workflow green on every push. |
| R-SI-1 zero new `*`           | [`.github/workflows/no_star.yaml`](../.github/workflows/no_star.yaml) | Workflow green on every push. |
| Yosys `$mul` audit            | [`.github/workflows/test.yaml`](../.github/workflows/test.yaml) | `R-SI-1 audit (Yosys)` job green. |
| GDS / shuttle                 | [`.github/workflows/gds.yaml`](../.github/workflows/gds.yaml) | `gds` job green; artefact uploaded. |
| Triple-Deck completeness      | [`TRIPLE_DECK_STATUS.md`](../TRIPLE_DECK_STATUS.md) §3 table | All three rows reach at least SYNTH. **target** |
| NMSE report present           | `bench/nmse/*.json` (planned dir) | At least one report file checked in. **target** |
| 22FDX notebook reproducible   | `bench/22fdx/` (planned dir) | Notebook regenerates the table in [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md) §2. **target** |
| Coq trace for CL-02           | `coq/` or `trios-coq/` | At least one `.v` file under `coq/` with the identity goal. **target** |

No row of this table treats funding, programme acceptance, or paper
publication as a success metric — those are outside this repo's
verification surface.

---

## 9. References

Only references that already appear in this repo, or are clearly
linkable from a public page, are listed. Anything else is `VERIFY`.

- DOI `10.5281/zenodo.19227877` — TRI-NET Trinity Stack provenance (anchored at TTSKY26b shuttle commit, see [`CHANGELOG.md`](../CHANGELOG.md)).
- DARPA CLARA programme page — <https://www.darpa.mil/research/programs/clara> (`VERIFY`).
- BitNet b1.58 — <https://arxiv.org/abs/2402.17764> (motivates the ternary substrate).
- PhD chapter (Ch. 36 TRI-1 Triad) — [flos_70.tex](https://github.com/gHashTag/trios/blob/main/docs/phd/chapters/flos_70.tex) (`VERIFY` against upstream repo HEAD).
- Tiny Tapeout shuttle catalogue — <https://tinytapeout.com/chips/> (`VERIFY`).
- [`TRI_NET_DARPA_CLARA_PROPOSAL.md`](TRI_NET_DARPA_CLARA_PROPOSAL.md) — proposal text, not a funded-programme record.
- [`CLARA_PROOF_MANIFEST.md`](CLARA_PROOF_MANIFEST.md) — proof status snapshot.
- [`INTERCONNECT_PROTOCOL_V1.md`](INTERCONNECT_PROTOCOL_V1.md) — Trinity Interconnect Protocol v1.0 (frozen at TTSKY26b).
- [`CROSS_TILE_INTERCONNECT.md`](CROSS_TILE_INTERCONNECT.md) — board-level wiring.
- [`HARDWARE_BRINGUP.md`](HARDWARE_BRINGUP.md), [`HARDWARE-IMPLEMENTATION.md`](HARDWARE-IMPLEMENTATION.md) — bring-up notes (pre-silicon).
- [`TRI_NET_FORMATS_SUMMARY.md`](TRI_NET_FORMATS_SUMMARY.md) — numeric format catalogue.
- [`TRI-NET 2026 plan` source]: `VERIFY` — this document is the φ-anchor adaptation; the line-level plan lives in coordinator notes outside this repo.

---

## 9.1 Filing pack — `.github/issues/`

The plan is **filed-but-not-filed**: 16 child issue markdown bodies +
one EPIC body live under [`.github/issues/`](../.github/issues/),
ready to be created as real GitHub issues by
[`.github/issues/create_issues.sh`](../.github/issues/create_issues.sh)
(default mode: dry-run).

| Index | Track | Body file |
|------:|-------|-----------|
| epic  | —      | [`00_EPIC_2026.md`](../.github/issues/00_EPIC_2026.md) |
| `#1`  | CL-01  | [`01_CL-01_d2d_drain_on_restraint.md`](../.github/issues/01_CL-01_d2d_drain_on_restraint.md) |
| `#2`  | CL-02  | [`02_CL-02_coq_lucas_post_trace.md`](../.github/issues/02_CL-02_coq_lucas_post_trace.md) |
| `#3`  | CL-03  | [`03_CL-03_ed25519_stub_spec.md`](../.github/issues/03_CL-03_ed25519_stub_spec.md) |
| `#4`  | CL-04  | [`04_CL-04_anchor_mismatch_flag.md`](../.github/issues/04_CL-04_anchor_mismatch_flag.md) |
| `#5`  | EN-01  | [`05_EN-01_rbb_capboost_stubs.md`](../.github/issues/05_EN-01_rbb_capboost_stubs.md) |
| `#6`  | EN-02  | [`06_EN-02_22fdx_projection_notebook.md`](../.github/issues/06_EN-02_22fdx_projection_notebook.md) |
| `#7`  | EN-03  | [`07_EN-03_refuse_ultra_headlines.md`](../.github/issues/07_EN-03_refuse_ultra_headlines.md) |
| `#8`  | SN-01  | [`08_SN-01_ternary_roundtrip_row.md`](../.github/issues/08_SN-01_ternary_roundtrip_row.md) |
| `#9`  | SN-02  | [`09_SN-02_spike_d2d_hook.md`](../.github/issues/09_SN-02_spike_d2d_hook.md) |
| `#10` | SN-03  | [`10_SN-03_anchor_stability_snn_burst.md`](../.github/issues/10_SN-03_anchor_stability_snn_burst.md) |
| `#11` | PUB-01 | [`11_PUB-01_whitepaper_pdf.md`](../.github/issues/11_PUB-01_whitepaper_pdf.md) |
| `#12` | PUB-02 | [`12_PUB-02_first_nmse_report.md`](../.github/issues/12_PUB-02_first_nmse_report.md) |
| `#13` | PUB-03 | [`13_PUB-03_clara_proof_note.md`](../.github/issues/13_PUB-03_clara_proof_note.md) |
| `#14` | OS-01  | [`14_OS-01_apache_open_pdk_posture.md`](../.github/issues/14_OS-01_apache_open_pdk_posture.md) |
| `#15` | OS-02  | [`15_OS-02_reference_host_bridge.md`](../.github/issues/15_OS-02_reference_host_bridge.md) |
| `#16` | OS-03  | [`16_OS-03_pr_template_r5_checklist.md`](../.github/issues/16_OS-03_pr_template_r5_checklist.md) |

The `#0`..`#16` labels are **local plan IDs**, not GitHub issue
numbers. GitHub will mint real numbers when a maintainer runs
[`create_issues.sh --apply`](../.github/issues/create_issues.sh).
The stable cross-reference handle is the **track ID** (`CL-01`,
`EN-02`, etc.) used throughout this document. See also
[`.github/issues/ISSUES_SUMMARY.md`](../.github/issues/ISSUES_SUMMARY.md).

---

## 10. What this document is NOT

- **Not** a funding announcement.
- **Not** a paper-acceptance announcement.
- **Not** a silicon-shipment notice.
- **Not** an update to [`BENCHMARKS.md`](../BENCHMARKS.md) measured rows. Any
  measurement that comes out of this plan lands as a separate PR that
  edits the MEASURED table directly.
- **Not** a license to quote `28–120 TOPS/W`, "1000×", or "4000 TOPS/W"
  as facts. Those numbers either stay labelled `projection` or stay
  out of the repo entirely.
