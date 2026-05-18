# TOPS/W — 22FDX Projection & Zenodo Bundle Readiness

> **Readiness:** **PROJECTED, PLAN ONLY**. Every number in this file is
> an architecture-level projection at 22FDX, not a measurement. There
> is **no measured silicon TOPS/W** in this repository (no φ-anchor die
> has been characterised), and the projections here MUST NOT be quoted
> as measurements. This file exists so that the existing 22FDX
> projection in [`README.md`](README.md#green-ai-manifesto) and
> [`BENCHMARKS.md`](BENCHMARKS.md#architecture-projections-projected-from-rtl-intent-only)
> has a stable, single-source landing page, and so the Zenodo bundle
> upgrade plan is visible.

Last updated: 2026-05-18.

---

## 1. Why a 22FDX projection at all

φ-anchor's demonstrator silicon is SKY130A (130 nm). At 130 nm, body
bias swing, leakage, and burst headroom are all node-limited
([`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) §2). The peer chips
that φ-anchor is compared against in [`COMPETITORS.md`](COMPETITORS.md)
are at 7 nm and below. To talk about TRI-NET's architectural energy
position **without lying about the demonstrator**, we project the same
RTL onto 22FDX (22 nm FD-SOI):

| Why 22FDX | Reason |
|-----------|--------|
| FD-SOI body-bias range  | Native ±1.5 V back-bias → both **RBB** and **FBB** decks of [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) become effective at this node. |
| Ternary-friendly        | Low Vth available, fits ternary {-1, 0, +1} small datapaths. |
| Open-tooling adjacent   | Documented PDKs exist; the projection is reproducible by other open teams (target — not yet automated in CI). |
| Industry-comparable     | Sits between bulk 28 nm and bleeding-edge 7/5 nm; honest middle ground. |

The projection is a **plan**, not a tape-out plan: this repo does not
commit a 22FDX RTL flow.

---

## 2. Projected envelope (architecture-level, not measured)

| Metric                | SKY130A (measured demonstrator) | 22FDX (PROJECTED, architecture) | Status |
|-----------------------|----------------------------------|----------------------------------|--------|
| TOPS/W (ternary)      | proof-of-concept node, **not a peak figure** | **28 – 120 TOPS/W**             | PROJECTED |
| Energy / GF16 dot4    | demonstrator-only                | low — small datapath, no DSP    | PROJECTED |
| Idle leakage          | not characterised                | reduced by RBB deck (planned)    | PROJECTED + deck not implemented |
| Burst headroom        | not characterised                | extended by CAP_BOOST (planned)  | PROJECTED + deck not implemented |
| Anchor latency (0x47C0) | 1 cycle combinational @50 MHz  | 1 cycle combinational at higher Fmax | RTL-level guarantee, not silicon |

Reading this table:

- The 28–120 TOPS/W range is the **same range** quoted in `README.md`
  and `BENCHMARKS.md`; this file is the canonical source for it.
- Both **RBB** and **CAP_BOOST** dependencies in this table are flagged
  as "deck not implemented" — see
  [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) §3. The projection
  assumes a future lineup includes them.
- "Peer-review pending" wording in the README should be read as:
  *no third-party reproduction of this projection has been done yet*.

---

## 3. Assumptions baked into the projection

These are listed so a reviewer can disagree on assumptions instead of
reverse-engineering them from a bullet point:

1. **Ternary {-1, 0, +1} ops dominate the workload.** The repo's
   datapath has no `*` ops (R-SI-1, see [`docs/R-SI-1.md`](docs/R-SI-1.md));
   ternary MACs reduce to controlled add/sub. At a node with FD-SOI
   back-bias and small datapaths, this is the regime where TOPS/W
   projections of this shape are plausible.
2. **Triple-Deck deployed in full** (RBB + FBB + CAP_BOOST). Today,
   φ-anchor implements **only FBB** ([`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md)).
   The projection therefore assumes a next-lineup chip, not this one.
3. **GF16 selected over bfloat16 where NMSE permits.** The NMSE
   protocol in [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) is the
   contract that gates this assumption. With no report in
   `bench/nmse/` today, this is a planning assumption only.
4. **No external accelerator** in the loop — TRI-NET dies stand alone
   on the TT shuttle board.
5. **22FDX library available** — assumed, not committed by this repo.

If any of these assumptions is violated, the 28–120 TOPS/W band moves.
The band itself is **not** quoted as a point estimate anywhere in the
repo, and that posture must be preserved.

---

## 4. Zenodo bundle — current and planned

| Artefact | Current Zenodo bundle | Planned upgrade |
|----------|------------------------|------------------|
| **DOI**                  | [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877) (TRI-NET Trinity Stack provenance) | Same DOI continues; new versions get new sub-DOIs as needed. |
| **TTSKY26b shuttle commit** | Anchored. | n/a |
| **`info.yaml` + RTL snapshot** | Anchored. | n/a |
| **Consolidated whitepaper PDF** | **Not yet uploaded**. | Upload after the NMSE harness ([`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md)) produces its first `bench/nmse/*.json`, so the PDF can cite measured (not projected) NMSE. |
| **22FDX projection notebook** | **Not in repo** (would compute the 28–120 TOPS/W band from the per-module estimates in [`BENCHMARKS.md`](BENCHMARKS.md) §"Cell-count snapshot"). | Land under `bench/22fdx/` once written; cross-link from this doc and from `BENCHMARKS.md`. |
| **CLARA evidence index**   | [`CLARA_TRACEABILITY.md`](CLARA_TRACEABILITY.md) in-repo | Upgrade to include external proof artefacts once `coq/` and `trios-coq/` are stabilised. |

The planned items are **plans**, not commitments — none of them have
PR-ready scope yet. They are listed here so the next lineup can pick
them up without rediscovering what's missing.

---

## 5. Acceptance criteria for replacing a row with a measurement

A "MEASURED" replacement for any row in §2 requires **all** of:

1. A physical TTSKY26b φ-anchor die (or a future 22FDX successor).
2. A characterisation harness committed under `bench/` with the raw
   capture data **and** the script that produced the table.
3. An update to [`BENCHMARKS.md`](BENCHMARKS.md) §"What is measured
   today" — never an edit of the projection section.
4. A CHANGELOG entry naming the die lot.
5. (For TOPS/W specifically) a power-rail capture under both
   `restraint_mode=0` and `restraint_mode=1` so the safety overhead is
   declared.

Anything short of all five stays in this file as a projection.

---

## 6. Cross-references

- [`BENCHMARKS.md`](BENCHMARKS.md) — measured vs projected; this file
  is the canonical source for the 22FDX projection cited there.
- [`STATUS.md`](STATUS.md) — readiness ladder.
- [`TRIPLE_DECK_STATUS.md`](TRIPLE_DECK_STATUS.md) — power-deck status
  that the projection depends on.
- [`GF16_BFLOAT16_NMSE.md`](GF16_BFLOAT16_NMSE.md) — numeric assumption
  that the projection depends on.
- [`COMPETITORS.md`](COMPETITORS.md) — peer-chip nodes for context.
- [`WHITEPAPER.md`](WHITEPAPER.md) — narrative hub.
- [Zenodo 10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877) — current bundle.
