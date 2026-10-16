#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Targeted sweep of gf16_v2_add with a zero operand, plus one negative control.

Policy: specs/physical/gf16_dot4_addnorm_probe.t27 section 5 (zero operands enter the adder arithmetic with
significand 0; the separate zero output branches are gone). This script checks that change on its own
boundary; the full unit sweeps (test/unit_sweeps.py) still run afterwards and are not replaced.

Vectors: a = +0 (0x0000) and -0 (0x8000) against every 16-bit code b (65536), in BOTH argument orders:
2 x 65536 x 2 = 262144 vectors, exactly the capacity of test/unit_tb.v (one run). Every expected result,
also for NaN / Inf / zero / E = 0 codes, comes from the unchanged exact oracle test/gf16_oracle.py; the bench
only compares (`!==`, so X never passes). The vector 0x0000 + 0x0001 is required to be in the set.

Negative control (a temporary copy only; the repository and the production RTL have no fault hooks): the
low significand gets the hidden 1 back even for a zero (`{~zero_lo, ...}` -> `{1'b1, ...}`). The same bench
and vectors must then report a real mismatch, among them 0x0000 + 0x0001. The control counts as KILLED only
if the replaced text was found exactly once, the copy compiled, the bench printed a complete result line for
all 262144 vectors with MISMATCH > 0, and the mismatch list shows a=0000 b=0001. A missing mutation text, a
compile error or a missing result line is an ERROR, never KILLED.

Usage (repo root): python3 test/add_zero_sweep.py [--out DIR]
Needs iverilog + vvp; Python 3 standard library only. Exit 0 = 0 mismatches AND the control KILLED.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_ADD = os.path.join(ROOT, "src", "gf16_v2_add.v")
# the adder uses the full-adder wrapper gf16_fa1 of this file; it is always the real, unmodified source
# (also for the temporary mutant, of which only the adder file is a copy)
SRC_FA = os.path.join(ROOT, "src", "gf16_sig_mul10.v")
sys.path.insert(0, HERE)
import gf16_oracle as orc  # noqa: E402

ZEROS = (0x0000, 0x8000)
EXPECT_N = 2 * 65536 * 2
MUTATION = ("wire [9:0]  sig_sml = {~zero_lo, mg_lo[8:0]};",
            "wire [9:0]  sig_sml = {1'b1, mg_lo[8:0]};")
RESULT_RE = re.compile(r"UNIT_RESULT add N=(\d+) MISMATCH=(\d+)")


def vectors():
    pairs = []
    for z in ZEROS:
        pairs += [(z, b) for b in range(65536)]
        pairs += [(b, z) for b in range(65536)]
    return pairs


def write_hex(path, words):
    with open(path, "w") as f:
        f.write("\n".join("%04x" % w for w in words) + "\n")


def build_and_run(add_src, tmp, tag, files, n=EXPECT_N):
    exe = os.path.join(tmp, "unit_add_" + tag)
    c = subprocess.run(["iverilog", "-g2012", "-DUNIT_ADD", "-o", exe, os.path.join(HERE, "unit_tb.v"), add_src,
                        SRC_FA], capture_output=True, text=True)
    if c.returncode != 0:
        return {"compiled": False, "stdout": "", "stderr": c.stderr[-2000:], "n": None, "mismatch": None, "exit": None}
    fa, fb, fe = files
    r = subprocess.run(["vvp", exe, "+A=" + fa, "+B=" + fb, "+E=" + fe, "+N=%d" % n],
                       capture_output=True, text=True)
    m = RESULT_RE.search(r.stdout)
    return {"compiled": True, "stdout": r.stdout[-4000:], "stderr": r.stderr[-1000:], "exit": r.returncode,
            "n": int(m.group(1)) if m else None, "mismatch": int(m.group(2)) if m else None,
            "unit_error": "UNIT_ERROR" in r.stdout}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="add-zero-sweep")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    problems = []
    pairs = vectors()
    if len(pairs) != EXPECT_N or len(set(pairs)) != len(pairs) - 4:
        # (z, z') pairs of the two zeros appear in both halves: (0,0), (0,8000), (8000,0), (8000,8000) twice each
        problems.append("vector set has %d entries / %d distinct, expected %d / %d"
                        % (len(pairs), len(set(pairs)), EXPECT_N, EXPECT_N - 4))
    if (0x0000, 0x0001) not in pairs or (0x0001, 0x0000) not in pairs:
        problems.append("0x0000 + 0x0001 is missing from the vector set")
    expected = [orc.add(a, b) for a, b in pairs]
    summary = {"vectors": len(pairs), "zero_codes": ["%04x" % z for z in ZEROS], "orders": 2,
               "oracle": "test/gf16_oracle.py add()", "production": None, "negative_control": None}
    with tempfile.TemporaryDirectory() as tmp:
        files = tuple(os.path.join(tmp, n) for n in ("a.hex", "b.hex", "e.hex"))
        write_hex(files[0], [p[0] for p in pairs])
        write_hex(files[1], [p[1] for p in pairs])
        write_hex(files[2], expected)

        prod = build_and_run(SRC_ADD, tmp, "production", files)
        summary["production"] = {k: prod[k] for k in ("compiled", "exit", "n", "mismatch")}
        with open(os.path.join(args.out, "production.log"), "w") as f:
            f.write(prod["stdout"] + "\n--- stderr ---\n" + prod["stderr"])
        if not prod["compiled"]:
            problems.append("production gf16_v2_add.v does not compile: %s" % prod["stderr"][-500:])
        elif prod["exit"] != 0 or prod["n"] != EXPECT_N or prod["mismatch"] != 0 or prod.get("unit_error"):
            problems.append("production sweep: exit %s, N=%s, MISMATCH=%s (need %d and 0)"
                            % (prod["exit"], prod["n"], prod["mismatch"], EXPECT_N))

        with open(SRC_ADD) as f:
            text = f.read()
        old, new = MUTATION
        found = text.count(old)
        ctl = {"text_found": found, "verdict": None}
        if found != 1:
            ctl["verdict"] = "ERROR"
            problems.append("negative control: mutation text found %d times (must be exactly 1)" % found)
        else:
            mdir = os.path.join(tmp, "mutant")
            os.makedirs(mdir)
            mpath = os.path.join(mdir, "gf16_v2_add.v")
            with open(mpath, "w") as f:
                f.write(text.replace(old, new))
            shutil.copy(mpath, os.path.join(args.out, "negative-control-gf16_v2_add.v"))
            mut = build_and_run(mpath, tmp, "mutant", files)
            ctl.update({k: mut[k] for k in ("compiled", "exit", "n", "mismatch")})
            with open(os.path.join(args.out, "negative-control.log"), "w") as f:
                f.write(mut["stdout"] + "\n--- stderr ---\n" + mut["stderr"])
            near_zero = "a=0000 b=0001" in mut["stdout"]
            ctl["mismatch_on_0000_plus_0001"] = near_zero
            if not mut["compiled"]:
                ctl["verdict"] = "ERROR"
                problems.append("negative control: the mutated copy does not compile (not a verdict)")
            elif mut["n"] != EXPECT_N or mut["mismatch"] is None or mut.get("unit_error"):
                ctl["verdict"] = "ERROR"
                problems.append("negative control: no complete result line (N=%s)" % mut["n"])
            elif mut["mismatch"] > 0 and near_zero:
                ctl["verdict"] = "KILLED"
            else:
                ctl["verdict"] = "SURVIVED"
                problems.append("negative control SURVIVED: MISMATCH=%s, 0x0000+0x0001 caught=%s"
                                % (mut["mismatch"], near_zero))
        summary["negative_control"] = ctl

    summary["status"] = "FAIL" if problems else "PASS"
    summary["problems"] = problems
    with open(os.path.join(args.out, "add-zero-sweep.json"), "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    print("ADD_ZERO_SWEEP %s vectors=%d production_mismatch=%s negative_control=%s mutant_mismatch=%s"
          % (summary["status"], len(pairs), summary["production"]["mismatch"],
             summary["negative_control"]["verdict"], summary["negative_control"].get("mismatch")))
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
