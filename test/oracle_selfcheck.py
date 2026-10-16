#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-check of the exact oracle, the conformance vectors and the pin model.

No DUT, no simulator. It checks, fail closed:
  1. hand-derived rounding facts (ties of MUL toward zero, ties of ADD to even, flush rules);
  2. the oracle's rounding against an independent code-space derivation (bisect over all
     32255 positive finite codes), for random values AND for exact halfway points;
  3. every vector in conformance/gf16_dot4_sky26d_vectors.json equals the oracle;
  4. the executable spec (t27_exec.py) agrees with the oracle (classes, NaN rules) and
     with the pin model (read map, status);
  5. the reorder counterexample exists.
Usage: python3 test/oracle_selfcheck.py [--quick]     (exit 0 = all checks pass)
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gf16_oracle as orc
import t27_exec
from pin_model import PinModel

VECTORS = os.path.join(HERE, "conformance", "gf16_dot4_sky26d_vectors.json")
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL:", msg)


def hand_facts():
    check(orc.mul(0x3E10, 0x3E30) == 0x3E41, "MUL tie must go toward zero (0x3E41)")
    check(orc.add(0x3E00, 0x2A00) == 0x3E00, "ADD tie 1 + 2^-10 must stay at the even 1.0")
    check(orc.add(0x3E01, 0x2A00) == 0x3E02, "ADD tie (1+2^-9) + 2^-10 must go to the even 0x3E02")
    check(orc.add(0x3E02, 0xAA01) == 0x3E01, "subtraction just below a tie must round down")
    check(orc.add(0x3E00, 0xBE00) == 0x0000, "1 - 1 must be +0")
    check(orc.add(0x8000, 0x8000) == 0x0000, "-0 + -0 must be +0")
    check(orc.add(0x8000, 0x3E00) == 0x3E00, "-0 + 1.0 must be 1.0")
    check(orc.mul(0x8000, 0x3E00) == 0x0000, "-0 * 1.0 must be +0")
    check(orc.mul(0x0200, 0x3C00) == 0x0000, "2^-31 has no code: flush to +0")
    check(orc.mul(0x0201, 0x3C00) == 0x0001, "(1+2^-9)*2^-31 is the smallest code 0x0001")
    check(orc.mul(0x7C00, 0x4000) == 0x7E00, "2^32 overflows to +Inf")
    check(orc.mul(0xFC00, 0x4000) == 0xFE00, "-2^32 overflows to -Inf")
    check(orc.mul(0x7E00, 0x0000) == 0xFE01, "Inf * 0 is NaN")
    check(orc.mul(0x0000, 0xFE00) == 0xFE01, "0 * -Inf is NaN")
    check(orc.add(0x7E00, 0xFE00) == 0xFE01, "Inf + -Inf is NaN")
    check(orc.add(0xFE00, 0xFE00) == 0xFE00, "-Inf + -Inf is -Inf")
    check(orc.add(0x7E01, 0x3E00) == 0xFE01 and orc.mul(0x3E00, 0xFFFF) == 0xFE01,
          "any NaN gives 0xFE01")
    check(orc.dot4([0x3E00, 0x4000, 0x4100, 0x4200], [0x3E00, 0x4000, 0x4100, 0x4200]) == 0x47C0,
          "DOT4 self-test must be 0x47C0")


def codespace_cross(rng, n):
    bad = 0
    tested = 0
    for i in range(n):
        a, b = orc.rand_code(rng), orc.rand_code(rng)
        ca, _ = orc.classify(a)
        cb, _ = orc.classify(b)
        if ca != "fin" or cb != "fin":
            continue
        for mode, q in (("tz", orc.value(a) * orc.value(b)), ("rne", orc.value(a) + orc.value(b))):
            ref = orc.round_code_by_codespace(q, mode)
            if ref is None:
                continue
            tested += 1
            got = orc.round_code(q, mode)
            if got != ref:
                bad += 1
                if bad <= 5:
                    print("codespace mismatch mode=%s q=%s oracle=0x%04x codespace=0x%04x"
                          % (mode, q, got, ref))
    # exact halfway points between neighbouring codes: tie rules in code space
    for i in range(n):
        e = rng.randint(0, 62)
        m = rng.randint(0, 510)
        if e == 0 and m == 0:
            continue
        mid = (orc.em_value(e, m) + orc.em_value(e, m + 1)) / 2
        sign = rng.getrandbits(1)
        q = -mid if sign else mid
        for mode in ("tz", "rne"):
            ref = orc.round_code_by_codespace(q, mode)
            if ref is None:
                continue
            tested += 1
            got = orc.round_code(q, mode)
            if got != ref:
                bad += 1
                if bad <= 5:
                    print("halfway mismatch mode=%s e=%d m=%d oracle=0x%04x codespace=0x%04x"
                          % (mode, e, m, got, ref))
    check(bad == 0, "oracle vs code-space derivation: %d mismatches" % bad)
    check(tested > n, "code-space cross-check tested too few values (%d)" % tested)
    return tested


def conformance():
    with open(VECTORS) as f:
        data = json.load(f)
    names = set()
    for v in data["vectors"]:
        check(v["name"] not in names, "duplicate vector name " + v["name"])
        names.add(v["name"])
        check(len(v["A"]) == 4 and len(v["B"]) == 4, "vector %s needs 4+4 words" % v["name"])
        A = [int(x, 16) for x in v["A"]]
        B = [int(x, 16) for x in v["B"]]
        exp = int(v["expected"], 16)
        got = orc.dot4(A, B)
        check(got == exp, "vector %s: expected 0x%04x but the oracle says 0x%04x"
              % (v["name"], exp, got))
    return len(data["vectors"])


def spec_vs_oracle_and_model(rng, quick):
    env, _ = t27_exec.load_spec()
    # classes over the whole code space
    for code in range(0x10000):
        cls, _ = orc.classify(code)
        check(env["dot4_is_zero"](code) == (cls == "zero"), "spec is_zero(0x%04x)" % code)
        check(env["dot4_is_inf"](code) == (cls == "inf"), "spec is_inf(0x%04x)" % code)
        check(env["dot4_is_nan"](code) == (cls == "nan"), "spec is_nan(0x%04x)" % code)
        check(env["dot4_exp"](code) == (code >> 9) & 0x3F, "spec exp(0x%04x)" % code)
        check(env["dot4_mant"](code) == code & 0x1FF, "spec mant(0x%04x)" % code)
        if len(failures) > 20:
            return
    pairs = [(a, b) for a in orc.SPECIAL_CODES for b in orc.SPECIAL_CODES]
    pairs += [(orc.rand_code(rng), orc.rand_code(rng)) for _ in range(2000 if quick else 20000)]
    for a, b in pairs:
        check(env["dot4_mul_is_nan"](a, b) == (orc.mul(a, b) == orc.NAN),
              "spec mul_is_nan(0x%04x,0x%04x) vs oracle" % (a, b))
        check(env["dot4_add_is_nan"](a, b) == (orc.add(a, b) == orc.NAN),
              "spec add_is_nan(0x%04x,0x%04x) vs oracle" % (a, b))
        check(env["dot4_canon_zero"](a) == (0 if orc.classify(a)[0] == "zero" else a),
              "spec canon_zero(0x%04x)" % a)
    # read map and status against the pin model
    for _ in range(2000 if quick else 20000):
        m = PinModel()
        m.mem = [rng.getrandbits(8) for _ in range(16)]
        m.ptr = rng.getrandbits(4)
        m.err = rng.getrandbits(1)
        m.done = rng.getrandbits(1)
        m.busy = rng.getrandbits(1)
        m.acc = rng.getrandbits(16)
        ui = rng.getrandbits(8)
        uio = rng.getrandbits(8)
        rsel = env["dot4_rsel"](uio)
        cell = m.mem[env["dot4_rb_addr"](ui)]
        spec_status = env["dot4_status"](m.ptr, m.err, m.done, m.busy)
        check(spec_status == m.status(), "spec status vs model")
        check(env["dot4_read_byte"](rsel, spec_status, m.acc, m.busy, cell) == m.read(ui, uio),
              "spec read_byte vs model (rsel=%d busy=%d)" % (rsel, m.busy))
        check(env["dot4_wr_bit"](uio) == (uio & 1) and env["dot4_go_bit"](uio) == (uio >> 1) & 1,
              "spec WR/GO bit decode")
    for p in range(16):
        check(env["dot4_ptr_next"](p) == (p + 1) % 16, "spec ptr_next(%d)" % p)
        check(env["dot4_ptr_operand"](p) == (1 if p >= 8 else 0), "spec ptr_operand(%d)" % p)
        check(env["dot4_ptr_lane"](p) == (p % 8) // 2, "spec ptr_lane(%d)" % p)
        check(env["dot4_ptr_hi"](p) == p % 2, "spec ptr_hi(%d)" % p)


def main(argv):
    quick = "--quick" in argv
    rng = random.Random(7)
    hand_facts()
    nvec = conformance()
    tested = codespace_cross(rng, 3000 if quick else 30000)
    spec_vs_oracle_and_model(rng, quick)
    A, B, left, tree = orc.find_reorder_counterexample()
    check(left != tree, "reorder counterexample must differ")
    if failures:
        print("ORACLE_SELFCHECK FAIL: %d failed checks" % len(failures))
        return 1
    print("ORACLE_SELFCHECK PASS: hand facts, %d conformance vectors, %d code-space values, "
          "spec/oracle/model agreement, reorder counterexample A=%s B=%s left=0x%04x tree=0x%04x"
          % (nvec, tested, ["0x%04x" % x for x in A], ["0x%04x" % x for x in B], left, tree))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
