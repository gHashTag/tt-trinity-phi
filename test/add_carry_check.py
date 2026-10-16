#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generic-branch check of the ADD significand ripple chain, plus one negative control.

Policy: specs/physical/gf16_dot4_addnorm_probe.t27 section 6. Vectors: test/add_vectors.py carry_pairs()
(deterministic adversarial set + the ADD steps of the DOT4 conformance vectors); expected results from the
unchanged exact oracle test/gf16_oracle.py; the unchanged bench test/unit_tb.v compares (default SETTLE).
The production adder (src/gf16_v2_add.v + src/gf16_sig_mul10.v) must give N = len(set) and MISMATCH = 0.

Negative control (temporary copy of the adder file only; the production RTL has no fault hooks): the carry seed
`c_seed = eff_sub` becomes `c_seed = 1'b0`, i.e. a subtraction without its +1. KILLED only if the replaced text
occurs exactly once, the copy compiles together with the real gf16_sig_mul10.v, the bench prints a complete
result line for all vectors with MISMATCH > 0, and at least one printed mismatch has two finite nonzero
operands of different sign (a real cancellation / borrow case). A missing text, a compile error, a missing or
incomplete result line is an ERROR, never KILLED. This control is in addition to the 18 pin-level controls of
test/mutation_runner.py and the zero-operand control of test/add_zero_sweep.py; it replaces none of them.

Usage (repo root): python3 test/add_carry_check.py [--out DIR]
Needs iverilog + vvp; Python 3 standard library only. Exit 0 = 0 mismatches AND the control KILLED.
"""
import argparse
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gf16_oracle as orc  # noqa: E402
import add_vectors  # noqa: E402
import add_zero_sweep as azs  # noqa: E402  (build_and_run, write_hex: same bench, same compile list)

MAXN = 262144
SEED_MUTATION = ("wire        c_seed = eff_sub;", "wire        c_seed = 1'b0;")
MISMATCH_RE = re.compile(r"MISMATCH i=\d+ a=([0-9a-fA-F]{4}) b=([0-9a-fA-F]{4})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="add-carry-check")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    problems = []
    pairs = add_vectors.carry_pairs()
    n = len(pairs)
    if not 0 < n <= MAXN:
        problems.append("vector set has %d entries, the bench holds 1..%d" % (n, MAXN))
    if not any(add_vectors.finite_nonzero_opposite(a, b) for a, b in pairs[:10]):
        problems.append("the set does not start with finite nonzero operands of different sign")
    expected = [orc.add(a, b) for a, b in pairs]
    summary = {"vectors": n, "conformance_add_steps": len(add_vectors.conformance_add_pairs()),
               "oracle": "test/gf16_oracle.py add()", "production": None, "negative_control": None}
    with tempfile.TemporaryDirectory() as tmp:
        files = tuple(os.path.join(tmp, x) for x in ("a.hex", "b.hex", "e.hex"))
        azs.write_hex(files[0], [p[0] for p in pairs])
        azs.write_hex(files[1], [p[1] for p in pairs])
        azs.write_hex(files[2], expected)

        prod = azs.build_and_run(azs.SRC_ADD, tmp, "carry_production", files, n)
        summary["production"] = {k: prod[k] for k in ("compiled", "exit", "n", "mismatch")}
        with open(os.path.join(args.out, "production.log"), "w") as f:
            f.write(prod["stdout"] + "\n--- stderr ---\n" + prod["stderr"])
        if not prod["compiled"]:
            problems.append("production adder does not compile: %s" % prod["stderr"][-500:])
        elif prod["exit"] != 0 or prod["n"] != n or prod["mismatch"] != 0 or prod.get("unit_error"):
            problems.append("production carry check: exit %s, N=%s, MISMATCH=%s (need %d and 0)"
                            % (prod["exit"], prod["n"], prod["mismatch"], n))

        with open(azs.SRC_ADD) as f:
            text = f.read()
        old, new = SEED_MUTATION
        ctl = {"text_found": text.count(old), "verdict": None}
        if ctl["text_found"] != 1:
            ctl["verdict"] = "ERROR"
            problems.append("carry-seed control: mutation text found %d times (must be exactly 1)" % ctl["text_found"])
        else:
            mdir = os.path.join(tmp, "mutant")
            os.makedirs(mdir)
            mpath = os.path.join(mdir, "gf16_v2_add.v")
            with open(mpath, "w") as f:
                f.write(text.replace(old, new))
            with open(mpath) as f, open(os.path.join(args.out, "negative-control-gf16_v2_add.v"), "w") as g:
                g.write(f.read())
            mut = azs.build_and_run(mpath, tmp, "carry_mutant", files, n)
            ctl.update({k: mut[k] for k in ("compiled", "exit", "n", "mismatch")})
            with open(os.path.join(args.out, "negative-control.log"), "w") as f:
                f.write(mut["stdout"] + "\n--- stderr ---\n" + mut["stderr"])
            shown = [(int(a, 16), int(b, 16)) for a, b in MISMATCH_RE.findall(mut["stdout"])]
            real = [p for p in shown if add_vectors.finite_nonzero_opposite(*p)]
            ctl["shown_mismatches"] = ["%04x+%04x" % p for p in shown]
            ctl["finite_opposite_sign_mismatch"] = bool(real)
            if not mut["compiled"]:
                ctl["verdict"] = "ERROR"
                problems.append("carry-seed control: the mutated copy does not compile (not a verdict)")
            elif mut["n"] != n or mut["mismatch"] is None or mut.get("unit_error"):
                ctl["verdict"] = "ERROR"
                problems.append("carry-seed control: no complete result line (N=%s)" % mut["n"])
            elif mut["mismatch"] > 0 and real:
                ctl["verdict"] = "KILLED"
            else:
                ctl["verdict"] = "SURVIVED"
                problems.append("carry-seed control SURVIVED: MISMATCH=%s, finite opposite-sign mismatch shown=%s"
                                % (mut["mismatch"], bool(real)))
        summary["negative_control"] = ctl

    summary["status"] = "FAIL" if problems else "PASS"
    summary["problems"] = problems
    with open(os.path.join(args.out, "add-carry-check.json"), "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    print("ADD_CARRY_CHECK %s vectors=%d production_mismatch=%s negative_control=%s mutant_mismatch=%s"
          % (summary["status"], n, summary["production"]["mismatch"] if summary["production"] else None,
             summary["negative_control"]["verdict"] if summary["negative_control"] else None,
             summary["negative_control"].get("mismatch") if summary["negative_control"] else None))
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
