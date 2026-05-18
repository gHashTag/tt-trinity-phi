# RELEASE MANIFEST — tt-trinity-phi · verification hardening layer (v1.1.0-spec-verification)

> **Readiness:** **DEPOSITION PENDING.** This manifest enumerates the
> files, intended Zenodo metadata, related identifiers, and content
> hashes for the **next** tt-trinity-phi deposition. **No DOI has been
> minted for this release.** The existing line-level DOI
> [`10.5281/zenodo.19227877`](https://doi.org/10.5281/zenodo.19227877)
> covers the **prior** TRI-NET Trinity Stack provenance bundle and is
> not the DOI of this release.

Last updated: 2026-05-18.

---

## R5 honesty: no DOI minted until Zenodo deposition is published

The following are NOT allowed in this repository before a Zenodo
deposition for this release is published:

- Quoting a DOI for *this* release in `README.md`, `CHANGELOG.md`,
  `WHITEPAPER.md`, `BENCHMARKS.md`, or any other doc.
- Setting `doi` in `.zenodo.json` to anything other than the
  placeholder.
- Updating
  [`docs/VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md)
  row `VC-NM-6` to point to a new DOI.

This rule is the R5 source of truth for DOI provenance and is referenced
by `VC-NM-6` in the claims matrix. The spec gate
[`scripts/check_trinet_specs.sh`](../scripts/check_trinet_specs.sh)
treats `10.5281/zenodo.19227877` as the only accepted DOI in this
repository and would flag a new DOI quoted before deposition as a spec
violation.

---

## Intended metadata (template in `.zenodo.json`)

| Field | Value |
|---|---|
| `title`            | tt-trinity-phi — TRI-1 Phi (φ-anchor): verification hardening layer |
| `upload_type`      | software |
| `version`          | `1.1.0-spec-verification` |
| `license`          | Apache-2.0 |
| `access_right`     | open |
| `language`         | eng |
| `community`        | `tinytapeout` |
| `creators`         | Vasilev, Dmitrii (from `info.yaml` `project.author`). **Update before publication if other creators contributed.** |
| `keywords`         | `tinytapeout`, `sky130`, `open-silicon`, `asic`, `verilog`, `tri-net`, `phi-anchor`, `goldenfloat`, `ternary`, `fdsoi`, `22fdx`, `body-bias`, `verification`, `conformance` |
| `publication_date` | **set by Zenodo** at publication time; do not pre-populate |
| `doi`              | **placeholder only** in `.zenodo.json`; minted by Zenodo at publication |

---

## Related identifiers

| Identifier | Relation | Status |
|---|---|---|
| `10.5281/zenodo.19227877`             | `isPartOf`         | Published — prior Trinity Stack bundle. |
| `https://github.com/gHashTag/tt-trinity-phi`   | `isSupplementTo` | Public — source repository for this release. |
| `https://github.com/gHashTag/tt-trinity-euler` | `isPartOf`       | Public — sibling chip. |
| `https://github.com/gHashTag/tt-trinity-gamma` | `isPartOf`       | Public — sibling chip. |
| Concept DOI for this release          | `isVersionOf`      | **Placeholder** — minted by Zenodo. |

---

## Files in the deposition (verification layer)

The deposition is RTL-stable: it adds *no* new `src/*.v` files and *no*
behavioural changes to existing RTL. The new artefacts are docs, spec
JSON, the spec-gate script, and one CI workflow.

| Path | Purpose | SHA-256 (at time of writing) |
|---|---|---|
| `docs/VERIFICATION_CLAIMS_MATRIX.md`                  | Normative claims index. | `88cca7700282ed6c539163cc16ca394cd51e0466b0818a1e3cc6dd03e3400051` |
| `docs/vectors/nmse/gf16_vs_bfloat16.golden.json`      | Golden NMSE reference vectors. | `93c03f6680d42d628205b0914b776a4b06de2a6612ff3974f3fbf98b9414dc25` |
| `docs/vectors/nmse/README.md`                         | NMSE vector pack documentation. | (regenerate at deposition time) |
| `conformance/d2d/valid_header.json`                   | D2D: valid ANCHOR frame. | `7e67ea98c49b38424267b0042b67a09273c5c77b38fd7ae35169e0eb04201f82` |
| `conformance/d2d/bad_crc.json`                        | D2D: bad CRC → drop + retry. | `a85f131b7c2379ea2303c05d55c4db932a76fb27eae7375416fe044f78396138` |
| `conformance/d2d/unsupported_opcode.json`             | D2D: unsupported TYPE → silent drop. | `3a1a0fa7fc2d04eb36d5e217e006409e5a565a0f9ae54df197a6fe6ce8e63019` |
| `conformance/d2d/timeout_retry.json`                  | D2D: 3 retries → RESYNC. | `cccc38fefa6789b9810bacc8f140c9448d84079227433f7aa6cedb4017d74eab` |
| `conformance/d2d/multi_chip_ordering.json`            | D2D: wired-AND ACK, multi-chip ordering. | `ccd0443722312056dde11f1cc81722d35a8f90ba8c96b88c1b36cbc220db7191` |
| `conformance/d2d/README.md`                           | D2D vector pack documentation. | (regenerate at deposition time) |
| `docs/TRIPLE_DECKER_STATE_MACHINE.md`                 | `IDLE → RBB → FBB → CAP_BOOST → IDLE` + brownout/overcurrent fallback. | `0072f3c295af875a56f924f98bb236cb104b611c0b54a9b00a878530a6ef4be5` |
| `docs/ARCHITECTURE_QUICK_WINS.md`                     | phi-specific quick wins, repo-grounded + competitor-informed. | (regenerate at deposition time) |
| `scripts/check_trinet_specs.sh`                       | Spec CI gate (local + CI). | `f1a2d198b84187b033967b319ba562ddc19cb9a5504c6466617960904069cb7e` |
| `.github/workflows/spec-gate.yml`                     | CI wiring. | `0d2b5ed7cf02481cb07030aaac850940218d97b360b6087259b8cd2b32409e10` |
| `.zenodo.json`                                        | Deposition metadata template. | `4185a5517440b4d94d18f0f3ef3b7b240295c28df5fd72d56abcbf6417573c50` |

Hashes are advisory — regenerate from `git rev-parse HEAD` at
deposition time. The authoritative manifest at deposition will use
hashes captured against the published commit, not these.

To re-hash locally:

```bash
sha256sum docs/VERIFICATION_CLAIMS_MATRIX.md \
          docs/vectors/nmse/gf16_vs_bfloat16.golden.json \
          conformance/d2d/*.json \
          docs/TRIPLE_DECKER_STATE_MACHINE.md \
          scripts/check_trinet_specs.sh \
          .github/workflows/spec-gate.yml \
          .zenodo.json
```

---

## Pre-existing artefacts in this repo (NOT re-deposited as new content)

These belong to earlier releases and are merely cross-referenced from
the deposition bundle:

| Path | Status |
|---|---|
| `src/*.v` (48 files, listed in `info.yaml`)             | Part of prior TTSKY26b shuttle submission; no change in this release. |
| `test/tb.v`, `test/Makefile`, `test/test.py`            | Pre-existing cocotb harness. |
| `.github/workflows/{test,no_star,fpga,gds,sky130-nightly,tri-test}.yml` | Pre-existing; unchanged here. |
| `docs/{API,ARCHITECTURE,COMPARISON,...}.md`             | Pre-existing — see `docs/INDEX.md`. |
| `conformance/FORMAT-SPEC-001.json`                      | Pre-existing GoldenFloat numeric registry. |
| `specs/numeric/*.t27`, `specs/fpga/*.t27`               | Pre-existing format / FPGA specs. |
| `info.yaml`                                             | Pre-existing TT project metadata. Contains a TOPS/W string (75/405) that pre-dates this release and is acknowledged as a known overclaim by matrix row `VC-NM-1`; it is **not** reaffirmed by this deposition. |

---

## Verification before deposition

Run the spec gate. The gate MUST pass before deposition is published:

```bash
bash scripts/check_trinet_specs.sh
# expect: OK: TRI-NET spec gate passed.
```

The gate enforces R5 honesty for the deposition:
- The golden NMSE vector's `provenance.mode` is never `SILICON`.
- The matrix carries all required `VC-*` IDs.
- No doc cites an unknown `VC-*` id.

---

## Sequence to publish

1. Update `.zenodo.json` `creators` and `keywords` if any contributors
   are missing or new keywords apply.
2. Final-edit this file: re-run `sha256sum` and replace placeholder
   hashes; replace `"version"` if the release name changes; verify
   `creators` matches `info.yaml`.
3. Run `bash scripts/check_trinet_specs.sh` — must pass.
4. Tag the release: `git tag v1.1.0-spec-verification`.
5. Push the tag: `git push --tags`.
6. Create a Zenodo deposition (or let the GitHub→Zenodo webhook
   create one).
7. **Once Zenodo publishes**, capture the minted DOI and update:
   - `README.md` "Zenodo / DOI status" section.
   - `CHANGELOG.md` release entry.
   - `docs/VERIFICATION_CLAIMS_MATRIX.md` row `VC-NM-6` to add the
     new DOI alongside `10.5281/zenodo.19227877`.
   - `.zenodo.json` `related_identifiers` `isVersionOf` placeholder.

Until step 7 completes, the only DOI in this repo is the legacy
`10.5281/zenodo.19227877`.

---

## Cross-references

- [`docs/VERIFICATION_CLAIMS_MATRIX.md`](VERIFICATION_CLAIMS_MATRIX.md)  — claim index.
- [`docs/ARCHITECTURE_QUICK_WINS.md`](ARCHITECTURE_QUICK_WINS.md)        — phi-specific next steps.
- [`docs/TRIPLE_DECKER_STATE_MACHINE.md`](TRIPLE_DECKER_STATE_MACHINE.md) — power FSM contract.
- [`TOPS_W_22FDX_PROJECTION.md`](../TOPS_W_22FDX_PROJECTION.md)          — projection / Zenodo bundle plan.
- [`scripts/check_trinet_specs.sh`](../scripts/check_trinet_specs.sh)    — spec gate.
- [`.zenodo.json`](../.zenodo.json)                                      — deposition metadata template.
