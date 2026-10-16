#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Integer model of the 8/4/2/1 left-normalisation tree of src/gf16_v2_add.v (module gf16_add_norm14).

For ALL 2^14 = 16384 values of the 14-bit sum it checks, in plain integers, that the fixed-stage tree has the
same leading-zero count and the same left-aligned 14-bit word as the old definition (lz = 13 - position of the
leading one, 14 for zero; norm = x << lz, truncated to 14 bits, so 0 for zero), that the leading one of every
nonzero word lands on bit 13, and that every leading-one position 0..13 and the value 0 occur.
This checks the formulas of the rewrite, NOT the Verilog text: the real RTL module is compared on the same
16384 inputs by test/tb_add_norm14.v, run inside test/unit_sweeps.py, and the whole adder stays covered by the
unit sweeps against the exact Fraction oracle, the pin tests and the mutations.
Python 3 standard library only. Exit 0 = PASS.
"""
import sys

MASK = (1 << 14) - 1


def old_scheme(x):
    lz = 14
    for k in range(13, -1, -1):
        if (x >> k) & 1:
            lz = 13 - k
            break
    return lz, (x << lz) & MASK


def tree(x):
    s8 = 0 if (x >> 6) & 0xFF else 1
    n8 = ((x & 0x3F) << 8) if s8 else x
    s4 = 0 if (n8 >> 10) & 0xF else 1
    n4 = ((n8 & 0x3FF) << 4) & MASK if s4 else n8
    s2 = 0 if (n4 >> 12) & 0x3 else 1
    n2 = ((n4 & 0xFFF) << 2) & MASK if s2 else n4
    s1 = 1 if (not (n2 >> 13) & 1) and ((n2 >> 12) & 1) else 0
    norm = ((n2 & 0x1FFF) << 1) & MASK if s1 else n2
    return (s8 << 3) | (s4 << 2) | (s2 << 1) | s1, norm


def run():
    n = mismatch = 0
    positions = set()
    for x in range(1 << 14):
        n += 1
        lz, norm = tree(x)
        if (lz, norm) != old_scheme(x):
            mismatch += 1
            if mismatch <= 5:
                print("MISMATCH x=%s tree=%s old=%s" % (format(x, "014b"), (lz, format(norm, "014b")), old_scheme(x)))
        if x:
            positions.add(x.bit_length() - 1)
            if not (norm >> 13) & 1:
                mismatch += 1
    ok = n == 16384 and mismatch == 0 and positions == set(range(14))
    print("ADDNORM_MODEL %s N=%d MISMATCH=%d POSITIONS=%d" % ("PASS" if ok else "FAIL", n, mismatch, len(positions)))
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
