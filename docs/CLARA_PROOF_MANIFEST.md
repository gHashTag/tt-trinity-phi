# CLARA Proof Manifest — Phi (TRI-1 φ-anchor)

## Provenance
- **Tape-out**: Tiny Tapeout SKY 26b (TTSKY26b), 1×1 tile, project φ-anchor
- **DOI**: 10.5281/zenodo.19227877 (IsNewVersionOf forthcoming)
- **ORCID**: 0009-0008-4294-6159
- **Author**: Dmitrii Vasilev
- **Frozen at commit**: 243a3f1e800f1d5715501d6db512911f77be8dbe
- **Top module**: `tt_um_trinity_nano`
- **Sibling SKUs**: tt-trinity-euler (8×2, 10 Gaps), tt-trinity-gamma (8×4, neuromorphic flagship)

## Verified Gaps

### Gap-4: Bounded Rationality (CLARA TA1.4)

- **Statement**: The hardware agent cannot select an action of unbounded computational cost; `restraint_ctrl` forces output to `K_UNKNOWN` when cost exceeds the polynomial bound, guaranteeing polynomial-time decision closure.
- **Coq file**: `trinity-clara/theorems/gap_4.v` (external repo [gHashTag/trinity-clara](https://github.com/gHashTag/trinity-clara))
- **Status**: Qed (admitted: 0)
- **Hardware mapping**: `restraint_ctrl.v` — RTL module enforcing hard-wired K\_UNKNOWN forcing under bounded-cost gate
- **Invariant**: `cost_exceeded → output = K_UNKNOWN` (no unbounded search branch reachable in synthesis graph)

## RTL ↔ Proof Bindings

| Module | Proof | Property |
|---|---|---|
| `phi_anchor_post` | `gap_4.v` | φ² + φ⁻² = 3 (Lucas POST chain L₂…L₇) |
| `restraint_ctrl` | `clara_bound.v` | `rationality_polynomial` — decision in O(1) cycles |
| `trinity_friend_foe` | `identity.v` | `challenge_response_total` — ∀ challenge ∃ response |
| `gf16_dot4` | `anchor_0x47C0.v` | `dot4(1,2,3,4) = 0x47C0` (combinational, no latency) |
| `lucas_rom` | `lucas_seq.v` | `L_n = L_{n-1} + L_{n-2}`, L₂=3, L₃=4, …, L₇=29 |

## Anchor Invariant (cross-die)

- **Claim**: ∀ chip ∈ {Phi, Euler, Gamma}, after reset until `load_mode=1`: `{uio_out, uo_out} = 0x47C0`
- **Proof sketch**: Combinational `gf16_dot4(1.0, 2.0, 3.0, 4.0)` → `0x47C0` via `gf16_dot4.v`; `status_request` is gated; R-SI-1 ensures no `*` operators in synthesisable RTL (audited by `.github/workflows/tri-test.yml` job "R-SI-1 Compliance Check")
- **Theorem**: TG-TRIAD-X 36.1 (PhD Theorem 36.1, `docs/phd/chapters/flos_70.tex`)

## R-SI-1 Audit

- **Rule**: Zero standalone `*` (arithmetic multiply) operators in synthesisable RTL — all GF16 arithmetic uses addition-only `gf16_add.v` carry logic
- **CI workflow**: `.github/workflows/tri-test.yml`, job `R-SI-1 Compliance Check`
- **Latest run**: GREEN at commit `243a3f1e800f1d5715501d6db512911f77be8dbe`
- **Comment-stripping sed pattern**: `sed 's|/\*[^*]*\*\+\([^/*][^*]*\*\+\)*/||g; s|//.*||'` applied per-file before `grep '\*'`
- **Exception**: `gf16_mul.v` is grandfathered (legacy GF16 Karatsuba mantissa product, not instantiated in `tt_um_trinity_nano`)

## Reproducibility

```bash
git clone https://github.com/gHashTag/tt-trinity-phi
cd tt-trinity-phi
make -C test
gh workflow run gds.yaml --ref main
```

Coq proofs (external):
```bash
git clone https://github.com/gHashTag/trinity-clara
cd trinity-clara
coqc -R . TrinityClara theorems/gap_4.v
```

## Open Admits

None — all theorems in `trinity-clara/theorems/gap_4.v` carry `Qed`.

---

*Generated: TTSKY26b submission freeze. DOI: [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)*
