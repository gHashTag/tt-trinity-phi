#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent exact oracle for the GF16 DOT4 SKY26d contract.

Normative source: specs/numeric/gf16_dot4_sky26d.t27 (issue #100). This module is
written from that contract, in rational arithmetic, and shares no code or algorithm
with the RTL (no guard bits, no alignment shifters, no leading-zero counters).

Contract recap (GF16 = S1 E6 M9, bias 31):
  finite nonzero code: (-1)^S * (1 + M/512) * 2^(E-31), E in 0..62 (E=0 with M>0 is a
  normal number, hidden 1). E=0,M=0: zero (either sign accepted as input).
  E=63: M=0 Inf, M>0 NaN.
  For finite nonzero operands take the exact rational q = product or sum, then
    1. q == 0                    -> +0
    2. binade e with 2^e <= |q| < 2^(e+1), no limit on e; x = |q| / 2^e * 512
    3. round x to an integer in [512, 1024]:
         MUL: to nearest, a tie goes TOWARD ZERO (up only if frac(x) > 1/2)
         ADD: to nearest, a tie goes to the EVEN integer (exact RNE)
       1024 -> binade e+1, 512
    4. E = e + 31, M = sig - 512: E >= 63 -> signed Inf; E < 0 or (E == 0 and M == 0)
       -> +0; otherwise the code.
  Every arithmetic zero result is +0. NaN result is always 0xFE01.
DOT4 = left fold: acc = p0; acc = ADD(acc, p1); acc = ADD(acc, p2); r = ADD(acc, p3).
"""
import bisect
import random
from fractions import Fraction

BIAS = 31
NAN = 0xFE01
INF_POS = 0x7E00
INF_NEG = 0xFE00


def classify(code):
    """(class, sign) with class in zero / fin / inf / nan."""
    s = (code >> 15) & 1
    e = (code >> 9) & 0x3F
    m = code & 0x1FF
    if e == 63:
        return ("inf" if m == 0 else "nan", s)
    if e == 0 and m == 0:
        return ("zero", s)
    return ("fin", s)


def em_value(e, m):
    """Exact positive value of a finite code with exponent field e and mantissa m."""
    return Fraction(512 + m, 512) * Fraction(2) ** (e - BIAS)


def value(code):
    """Exact signed Fraction of a finite nonzero code."""
    q = em_value((code >> 9) & 0x3F, code & 0x1FF)
    return -q if (code >> 15) & 1 else q


def _ge_pow2(n, d, e):
    """n/d >= 2^e, exact."""
    return n >= (d << e) if e >= 0 else (n << (-e)) >= d


def floor_log2(m):
    """e with 2^e <= m < 2^(e+1) for a positive Fraction m."""
    n, d = m.numerator, m.denominator
    e = n.bit_length() - d.bit_length()
    if not _ge_pow2(n, d, e):
        e -= 1
    assert _ge_pow2(n, d, e) and not _ge_pow2(n, d, e + 1)
    return e


def round_code(q, mode):
    """Code of the exact rational q under the contract; mode 'tz' (MUL) or 'rne' (ADD)."""
    if q == 0:
        return 0x0000
    sign = 1 if q < 0 else 0
    m = -q if sign else q
    n, d = m.numerator, m.denominator
    e = floor_log2(m)
    # x = m / 2^e * 512 = N / D exactly
    if e >= 0:
        num, den = n << 9, d << e
    else:
        num, den = n << (9 - e), d
    fl, r = divmod(num, den)
    assert 512 <= fl <= 1023
    twice = 2 * r
    if mode == "tz":
        up = twice > den
    elif mode == "rne":
        up = twice > den or (twice == den and (fl & 1) == 1)
    else:
        raise ValueError(mode)
    sig = fl + (1 if up else 0)
    if sig == 1024:
        sig = 512
        e += 1
    ebias = e + BIAS
    mant = sig - 512
    if ebias >= 63:
        return (sign << 15) | INF_POS
    if ebias < 0 or (ebias == 0 and mant == 0):
        return 0x0000
    return (sign << 15) | (ebias << 9) | mant


def mul(a, b):
    ca, sa = classify(a)
    cb, sb = classify(b)
    if ca == "nan" or cb == "nan":
        return NAN
    if ca == "inf" or cb == "inf":
        if ca == "zero" or cb == "zero":
            return NAN
        return INF_POS | ((sa ^ sb) << 15)
    if ca == "zero" or cb == "zero":
        return 0x0000
    return round_code(value(a) * value(b), "tz")


def add(a, b):
    ca, sa = classify(a)
    cb, sb = classify(b)
    if ca == "nan" or cb == "nan":
        return NAN
    if ca == "inf" and cb == "inf":
        return a if sa == sb else NAN
    if ca == "inf":
        return a
    if cb == "inf":
        return b
    if ca == "zero" and cb == "zero":
        return 0x0000
    if ca == "zero":
        return b
    if cb == "zero":
        return a
    return round_code(value(a) + value(b), "rne")


def dot4(A, B):
    """Contract order: acc = p0, then three ADDs (left fold)."""
    p = [mul(A[k], B[k]) for k in range(4)]
    acc = p[0]
    for k in (1, 2, 3):
        acc = add(acc, p[k])
    return acc


def dot4_tree(A, B):
    """(p0+p1)+(p2+p3): the old baseline order, NOT the contract. Used to find a vector
    on which the order matters."""
    p = [mul(A[k], B[k]) for k in range(4)]
    return add(add(p[0], p[1]), add(p[2], p[3]))


# ---------------------------------------------------------------------------
# Independent code-space derivation (cross-check of round_code in range)
# ---------------------------------------------------------------------------
_TABLE = None


def _table():
    global _TABLE
    if _TABLE is None:
        rows = []
        for e in range(0, 63):
            for m in range(512):
                if e == 0 and m == 0:
                    continue
                rows.append((em_value(e, m), e, m))
        rows.sort()
        _TABLE = ([r[0] for r in rows], [(r[1], r[2]) for r in rows])
    return _TABLE


def round_code_by_codespace(q, mode):
    """Nearest representable magnitude by bisect over all 32255 positive finite codes.
    Returns None outside [smallest code, largest code], where the contract's flush and
    overflow rules (not nearest-code rounding) decide."""
    if q == 0:
        return None
    vals, codes = _table()
    sign = 1 if q < 0 else 0
    m = -q if sign else q
    if m < vals[0] or m > vals[-1]:
        return None
    i = bisect.bisect_left(vals, m)
    if vals[i] == m:
        e, mm = codes[i]
        return (sign << 15) | (e << 9) | mm
    dl = m - vals[i - 1]
    dh = vals[i] - m
    if dl < dh:
        pick = i - 1
    elif dh < dl:
        pick = i
    elif mode == "tz":
        pick = i - 1                      # tie toward zero: smaller magnitude
    else:                                 # tie to even mantissa
        pick = i - 1 if codes[i - 1][1] % 2 == 0 else i
    e, mm = codes[pick]
    return (sign << 15) | (e << 9) | mm


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------
SPECIAL_CODES = [
    0x0000, 0x8000, INF_POS, INF_NEG, NAN, 0x7E01, 0xFE02, 0x7FFF, 0xFFFF,
    0x0001, 0x8001, 0x0002, 0x7DFF, 0xFDFF, 0x7C00, 0x3E00, 0xBE00,
]


def rand_code(rng):
    """Random GF16 code: mostly finite with moderate exponents, some extremes/specials."""
    k = rng.random()
    if k < 0.04:
        return rng.choice(SPECIAL_CODES)
    s = rng.getrandbits(1) << 15
    if k < 0.15:
        e = rng.choice([0, 1, 2, 3, 59, 60, 61, 62])
    elif k < 0.55:
        e = rng.randint(27, 35)
    else:
        e = rng.randint(1, 62)
    return s | (e << 9) | rng.getrandbits(9)


def find_reorder_counterexample(seed=20261015, tries=300000):
    """Deterministically find (A, B) whose left-fold DOT4 differs from the tree order and
    whose results are both ordinary numbers. Fails closed when none is found."""
    rng = random.Random(seed)
    for _ in range(tries):
        A = [(rng.getrandbits(1) << 15) | (rng.randint(28, 34) << 9) | rng.getrandbits(9)
             for _ in range(4)]
        B = [(rng.getrandbits(1) << 15) | (rng.randint(24, 34) << 9) | rng.getrandbits(9)
             for _ in range(4)]
        left = dot4(A, B)
        tree = dot4_tree(A, B)
        if left != tree and classify(left)[0] in ("fin", "zero") \
                and classify(tree)[0] in ("fin", "zero"):
            return A, B, left, tree
    raise RuntimeError("no reorder counterexample found: oracle or search is broken")
