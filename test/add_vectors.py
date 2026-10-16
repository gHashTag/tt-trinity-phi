#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Deterministic ADD operand sets for the carry-chain checks (policy: specs/physical/gf16_dot4_addnorm_probe.t27
section 6). Only operand pairs are built here; every expected result is computed by the unchanged exact
oracle test/gf16_oracle.py in the calling script, and nothing here models the RTL.

adversarial_pairs():
  first, two blocks that need the subtraction carry: every finite nonzero code x of the grid against -x (exact
  cancellation) and against the negative of its neighbour one ulp above (borrow); then all ordered pairs of the
  grid {both signs} x {exponents near 0, near the far threshold, near the bias, near 62} x {edge mantissas}
  plus Inf, -Inf and three NaN codes. This covers different signs, cancellation, borrow, carry into the next
  binade and overflow (511 + 511 at E 62), ties (exponent difference 10 with M = 0), far jam (difference >= 13),
  E = 0 codes, zeros and specials.
conformance_add_pairs():
  the (acc, product) operands of the three ADD steps of every DOT4 vector in
  test/conformance/gf16_dot4_sky26d_vectors.json, in the contract order (acc = p0, then ADD with p1, p2, p3).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gf16_oracle as orc  # noqa: E402

E_LIST = (0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 29, 30, 31, 32, 49, 50, 51, 60, 61, 62)
M_LIST = (0, 1, 2, 3, 255, 256, 257, 509, 510, 511)
SPECIALS = (0x7E00, 0xFE00, 0x7E01, 0xFE01, 0x7FFF)
VECTORS = os.path.join(HERE, "conformance", "gf16_dot4_sky26d_vectors.json")


def grid_codes():
    return [(s << 15) | (e << 9) | m for s in (0, 1) for e in E_LIST for m in M_LIST]


def adversarial_pairs():
    grid = grid_codes()
    nonzero = [x for x in grid if x & 0x7FFF]
    pairs = [(x, x ^ 0x8000) for x in nonzero]                                    # exact cancellation
    pairs += [(x, (x ^ 0x8000) + 1) for x in nonzero if (x & 0x1FF) != 0x1FF]     # borrow: one ulp apart
    codes = grid + list(SPECIALS)
    pairs += [(a, b) for a in codes for b in codes]
    return pairs


def conformance_add_pairs():
    with open(VECTORS) as f:
        data = json.load(f)
    pairs = []
    for v in data["vectors"]:
        A = [int(x, 16) for x in v["A"]]
        B = [int(x, 16) for x in v["B"]]
        p = [orc.mul(A[k], B[k]) for k in range(4)]
        acc = p[0]
        for k in (1, 2, 3):
            pairs.append((acc, p[k]))
            acc = orc.add(acc, p[k])
    return pairs


def carry_pairs():
    """The set used by the carry checks: adversarial first (so the cancellation pairs lead), then conformance."""
    return adversarial_pairs() + conformance_add_pairs()


def finite_nonzero_opposite(a, b):
    ca, sa = orc.classify(a)
    cb, sb = orc.classify(b)
    return ca == "fin" and cb == "fin" and sa != sb
