#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Integer check of the two-binade rounding/exponent rewrite of src/gf16_v2_mul.v.

gf16_v2_mul feeds its significand multiplier with {1, M}, so the integer operands are 512..1023 and the
product P is 2^18 <= P <= 1023*1023 = 1046529. For EVERY one of the 512 * 512 = 262144 operand pairs this
script computes, in plain integers,
  * the ORIGINAL scheme: select the binade by P[19], keep 10 bits, round up iff the discarded part is
    strictly above half (tie toward zero), carry into the next binade, mantissa 0 on carry, exponent
    increment top + carry;
  * the NEW scheme of the RTL: both binades in parallel (up_lo, mant_lo, cy_lo, up_hi, mant_hi), the
    exponent increment is 1 when (top or cy_lo), else 0, the mantissa is selected by top;
and asserts that mantissa and exponent increment are identical, that the upper-binade rounding carry never
happens (the bound that allows dropping it), that the maximum product is 1046529, and that the lower-binade
carry IS exercised (so the carry path is not dead).
It checks the arithmetic argument and the formulas of the rewrite, not the Verilog text: the RTL itself is
checked by the unit sweeps against the exact Fraction oracle (all 512 x 512 mantissa pairs at the threshold
exponent sums), the pin tests and the mutations. It is NOT an exhaustive check of all 2^32 GF16 operand pairs,
and gf16_sig_mul10 still covers all 1024 x 1024 pairs on its own.
Python 3 standard library only. Exit 0 = PASS.
"""
import sys


def old_scheme(p):
    top = (p >> 19) & 1
    sig = (p >> 10) & 0x3FF if top else (p >> 9) & 0x3FF
    rem = p & 0x3FF if top else p & 0x1FF
    half = 512 if top else 256
    up = 1 if rem > half else 0
    sig_r = sig + up
    carry = (sig_r >> 10) & 1
    mant = 0 if carry else sig_r & 0x1FF
    return top, carry, mant, top + carry


def new_scheme(p):
    top = (p >> 19) & 1
    up_lo = ((p >> 8) & 1) & (1 if p & 0xFF else 0)
    mant_lo = (((p >> 9) & 0x1FF) + up_lo) & 0x1FF
    cy_lo = (1 if ((p >> 9) & 0x1FF) == 0x1FF else 0) & up_lo
    up_hi = ((p >> 9) & 1) & (1 if p & 0x1FF else 0)
    mant_hi = (((p >> 10) & 0x1FF) + up_hi) & 0x1FF
    sel30 = top | cy_lo
    return top, mant_hi if top else mant_lo, 1 if sel30 else 0


def run():
    n = mismatch = upper_carry = lower_carry = top_cases = 0
    max_p = 0
    for a in range(512, 1024):
        for b in range(512, 1024):
            p = a * b
            n += 1
            max_p = max(max_p, p)
            top, carry, mant, inc = old_scheme(p)
            ntop, nmant, ninc = new_scheme(p)
            if top and carry:
                upper_carry += 1
            if not top and carry:
                lower_carry += 1
            top_cases += top
            if (top, mant, inc) != (ntop, nmant, ninc):
                mismatch += 1
                if mismatch <= 5:
                    print("MISMATCH a=%d b=%d P=%d old=%s new=%s" % (a, b, p, (top, mant, inc), (ntop, nmant, ninc)))
    ok = (n == 512 * 512 and n == 262144 and mismatch == 0 and upper_carry == 0 and max_p == 1023 * 1023
          and max_p == 1046529 and lower_carry > 0 and top_cases > 0)
    print("MULPACK_BOUND %s N=%d MAX_P=%d UPPER_CARRY=%d LOWER_CARRY=%d TOP_CASES=%d MISMATCH=%d"
          % ("PASS" if ok else "FAIL", n, max_p, upper_carry, lower_carry, top_cases, mismatch))
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
