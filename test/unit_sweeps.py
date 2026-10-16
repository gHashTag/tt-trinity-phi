#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Isolated unit sweeps of gf16_v2_mul / gf16_v2_add against the exact Fraction oracle.

The expected result of EVERY vector is computed by gf16_oracle (exact rational arithmetic);
the Verilog bench test/unit_tb.v only compares. 0 bit mismatches are required.
Also runs the exhaustive shift-and-add check test/tb_sig_mul10.v (all 2^20 10x10 products
against an integer product).

Profiles (counts are printed; a quick run is NOT a full run and says so):
  quick  every exponent difference / sum, mantissas sampled (stride 37 + edge values)
  full   ADD: every exponent difference 0..62 x every sign relation x ALL 512x512 mantissa
              pairs (33,030,144 vectors); MUL: ALL 512x512 mantissa pairs for the 33 exponent
              sums around the underflow, carry and overflow thresholds, mantissa stride 7 for
              the other sums
  both   plus boundary sweeps (exponent sets near 0, near the bias and near 62, edge
         mantissas, all four sign combinations) and a class sweep (zero/Inf/NaN codes).

Usage (from the repo root):
  python3 test/unit_sweeps.py --profile quick --jobs 2
  python3 test/unit_sweeps.py --profile full  --jobs 4        # CI
Needs iverilog + vvp; Python 3 standard library only. Exit 0 = every sweep clean.
"""
import argparse
import multiprocessing
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, HERE)

import gf16_oracle as orc
import mul_pack_bound
import add_norm_check

CHUNK = 262144
E_SET = sorted(set(list(range(0, 13)) + list(range(26, 37)) + list(range(50, 63))))
M_SUB = [0, 1, 2, 3, 4, 127, 128, 255, 256, 257, 383, 384, 510, 511]


def enc(s, e, m):
    return (s << 15) | (e << 9) | m


def sample_mants(stride):
    return sorted(set(list(range(0, 512, stride)) + [0, 1, 2, 3, 254, 255, 256, 257, 509, 510, 511]))


def chunks_of(name, pairs):
    for i in range(0, len(pairs), CHUNK):
        yield (name, pairs[i:i + CHUNK])


def add_core(profile):
    mants = list(range(512)) if profile == "full" else sample_mants(37)
    for d in range(0, 63):
        eb = 40 if d <= 40 else d
        es = eb - d
        for rel in (0, 1):
            pairs = []
            for ma in mants:
                for mb in mants:
                    big = enc(0, eb, ma)
                    small = enc(rel, es, mb)
                    pairs.append((small, big) if (ma + mb) & 1 else (big, small))
            yield ("add_core d=%d rel=%d" % (d, rel), pairs)


def boundary_pairs():
    pairs = []
    for ea in E_SET:
        for eb in E_SET:
            for ma in M_SUB:
                for mb in M_SUB:
                    for sa, sb in ((0, 0), (0, 1), (1, 0), (1, 1)):
                        pairs.append((enc(sa, ea, ma), enc(sb, eb, mb)))
    return pairs


def class_pairs():
    codes = list(orc.SPECIAL_CODES) + [enc(s, 63, m) for s in (0, 1) for m in (0, 1, 255, 511)]
    codes += [enc(s, e, m) for s in (0, 1) for e in (0, 1, 31, 62) for m in (0, 1, 511)]
    return [(a, b) for a in codes for b in codes]


def mul_core(profile):
    window = set(range(28, 37)) | set(range(58, 67)) | set(range(90, 99)) | {0, 1, 2, 122, 123, 124}
    for s in range(125):
        if profile == "full" and s in window:
            mants = list(range(512))
        elif profile == "full":
            mants = sample_mants(7)
        else:
            mants = sample_mants(37)
        ea = s // 2
        eb = s - ea
        for rel in (0, 1):
            pairs = [(enc(0, ea, ma), enc(rel, eb, mb)) for ma in mants for mb in mants]
            yield ("mul_core sum=%d rel=%d" % (s, rel), pairs)


def all_tasks(op, profile):
    gen = add_core(profile) if op == "add" else mul_core(profile)
    for name, pairs in gen:
        yield (op, name, pairs)
    for name, pairs in chunks_of(op + "_boundary", boundary_pairs()):
        yield (op, name, pairs)
    yield (op, op + "_classes", class_pairs())


def expected(op, pairs):
    f = orc.add if op == "add" else orc.mul
    return [f(a, b) for a, b in pairs]


def build(op, outdir):
    exe = os.path.join(outdir, "unit_" + op)
    # the adder's significand sum uses the full-adder wrapper gf16_fa1 defined in gf16_sig_mul10.v
    srcs = [os.path.join(SRC, "gf16_v2_add.v"), os.path.join(SRC, "gf16_sig_mul10.v")] if op == "add" else \
        [os.path.join(SRC, "gf16_v2_mul.v"), os.path.join(SRC, "gf16_sig_mul10.v")]
    cmd = ["iverilog", "-g2012", "-o", exe] + (["-DUNIT_ADD"] if op == "add" else []) + \
        [os.path.join(HERE, "unit_tb.v")] + srcs
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("iverilog failed for %s:\n%s" % (op, r.stderr))
    return exe


def write_hex(path, words):
    with open(path, "w") as f:
        f.write("\n".join("%04x" % w for w in words))
        f.write("\n")


def run_task(job):
    op, name, pairs, exe, tmp = job
    exp = expected(op, pairs)
    tag = re.sub(r"[^A-Za-z0-9]+", "_", name) + "_%d" % os.getpid()
    fa, fb, fe = (os.path.join(tmp, "%s.%s.hex" % (tag, k)) for k in ("a", "b", "e"))
    write_hex(fa, [p[0] for p in pairs])
    write_hex(fb, [p[1] for p in pairs])
    write_hex(fe, exp)
    r = subprocess.run(["vvp", exe, "+A=" + fa, "+B=" + fb, "+E=" + fe, "+N=%d" % len(pairs)],
                       capture_output=True, text=True)
    for p in (fa, fb, fe):
        os.remove(p)
    m = re.search(r"UNIT_RESULT (\w+) N=(\d+) MISMATCH=(\d+)", r.stdout)
    ok = (r.returncode == 0 and m is not None and m.group(1) == op
          and int(m.group(2)) == len(pairs) and int(m.group(3)) == 0
          and "UNIT_ERROR" not in r.stdout)
    detail = "" if ok else (r.stdout[-1500:] + r.stderr[-500:])
    return (op, name, len(pairs), ok, detail)


def run_sig_mul(tmp):
    exe = os.path.join(tmp, "tb_sig_mul10")
    c = subprocess.run(["iverilog", "-g2012", "-o", exe, os.path.join(HERE, "tb_sig_mul10.v"),
                        os.path.join(SRC, "gf16_sig_mul10.v")], capture_output=True, text=True)
    if c.returncode != 0:
        print("iverilog failed for tb_sig_mul10:\n" + c.stderr)
        return False
    r = subprocess.run(["vvp", exe], capture_output=True, text=True)
    m = re.search(r"SIGMUL10_RESULT N=(\d+) MISMATCH=(\d+)", r.stdout)
    ok = r.returncode == 0 and m is not None and int(m.group(1)) == 1 << 20 and int(m.group(2)) == 0
    print("sig_mul10 exhaustive: %s (%s)" % ("PASS" if ok else "FAIL",
                                              m.group(0) if m else r.stdout[-300:]))
    return ok


def run_add_norm(tmp):
    """The real RTL module gf16_add_norm14 against the old leading-zero definition on all 2^14 inputs."""
    exe = os.path.join(tmp, "tb_add_norm14")
    c = subprocess.run(["iverilog", "-g2012", "-o", exe, os.path.join(HERE, "tb_add_norm14.v"),
                        os.path.join(SRC, "gf16_v2_add.v"), os.path.join(SRC, "gf16_sig_mul10.v")],
                       capture_output=True, text=True)
    if c.returncode != 0:
        print("iverilog failed for tb_add_norm14:\n" + c.stderr)
        return False
    r = subprocess.run(["vvp", exe], capture_output=True, text=True)
    m = re.search(r"ADDNORM14_RESULT N=(\d+) MISMATCH=(\d+)", r.stdout)
    ok = r.returncode == 0 and m is not None and int(m.group(1)) == 1 << 14 and int(m.group(2)) == 0
    print("add_norm14 exhaustive: %s (%s)" % ("PASS" if ok else "FAIL", m.group(0) if m else r.stdout[-300:]))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=("quick", "full"), default="quick")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", choices=("mul", "add"), default=None)
    args = ap.parse_args()
    t0 = time.time()
    ok_all = True
    totals = {"mul": 0, "add": 0}
    with tempfile.TemporaryDirectory() as tmp:
        ok_all &= run_sig_mul(tmp)
        ok_all &= mul_pack_bound.run()      # 512 x 512 integer pairs: upper carry bound + two-binade equivalence
        ok_all &= add_norm_check.run()      # 2^14 integer model of the 8/4/2/1 normaliser vs the old definition
        ok_all &= run_add_norm(tmp)         # the real RTL gf16_add_norm14 on the same 16384 inputs
        for op in ("mul", "add"):
            if args.only and args.only != op:
                continue
            exe = build(op, tmp)
            jobs = ((o, n, p, exe, tmp) for (o, n, p) in all_tasks(op, args.profile))
            with multiprocessing.Pool(args.jobs) as pool:
                while True:                      # bounded batches keep memory small
                    batch = [j for _, j in zip(range(args.jobs * 2), jobs)]
                    if not batch:
                        break
                    for (o, name, n, ok, detail) in pool.map(run_task, batch):
                        totals[o] += n
                        if not ok:
                            ok_all = False
                            print("FAIL %s %s (%d vectors)\n%s" % (o, name, n, detail))
            print("%s sweeps done: %d vectors so far" % (op, totals[op]))
    print("UNIT_SWEEPS %s profile=%s mul_vectors=%d add_vectors=%d seconds=%d%s"
          % ("PASS" if ok_all else "FAIL", args.profile, totals["mul"], totals["add"],
             time.time() - t0, "" if args.profile == "full" else "  (QUICK: sampled, not exhaustive)"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
