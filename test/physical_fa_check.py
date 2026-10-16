#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check the technology branch of the multiplier against the REAL PDK Verilog models.

src/gf16_sig_mul10.v has a generic full adder (simulation, host audit) and, under `__pnr__` (the
official LibreLane synthesis) or PHI_FA_PHYS, an instance of sky130_fd_sc_hd__fa_1. A simulation with
the generic branch proves nothing about the cell branch, so this script, run in CI after the Build
GDS step (the PDK is on the runner then), compiles the project with -DPHI_FA_PHYS together with the
pinned PDK's own `primitives.v` and `sky130_fd_sc_hd.v` and checks:
  1. the 8 truth cases of the PDK cell and of the project wrapper (test/tb_fa1_truth.v);
  2. all 2^20 operand pairs of the multiplier against the integer product (test/tb_sig_mul10.v,
     N = 1048576, MISMATCH = 0, exit code 0; anything unparsable or UNKNOWN is a FAIL);
  3. a negative control: the same multiplier with the cell's SUM and COUT outputs swapped must
     produce mismatches (a compile failure or a clean pass of the broken copy is a FAIL);
  4. the ACTIVE adder (src/gf16_v2_add.v, whose significand sum uses the same wrapper gf16_fa1, policy
     specs/physical/gf16_dot4_addnorm_probe.t27 section 6) with the unchanged bench test/unit_tb.v
     (-DUNIT_ADD, -Punit_tb.SETTLE=<settle>, the generic default 1 is not used here) on
       a. +0 and -0 against all 65536 codes in both orders (test/add_zero_sweep.py vectors(), N = 262144),
       b. the deterministic carry set test/add_vectors.py carry_pairs() (cancellation, borrow, different
          signs, carry, ties, far jam, edge exponents, NaN/Inf, zeros, ADD steps of the conformance vectors),
     expected results only from the unchanged oracle test/gf16_oracle.py; exact N and MISMATCH = 0;
  5. a negative control of the adder's chain in this branch: a temporary copy with the carry seed 0 instead
     of eff_sub (test/add_carry_check.py SEED_MUTATION) must compile and show a real mismatch on the carry set
     (complete count, MISMATCH > 0, a printed mismatch with two finite nonzero operands of different sign).
Provenance (PDK version, sha256 of both model files, simulator version) goes to the report. There is
no fallback model: if the pinned PDK Verilog is missing or ambiguous the check FAILS. A simulation of the
PDK model is not a layout or LVS proof; the gate-level pin test and the flow's LVS remain separate.
Diagnosis/measurement of the technology branch only; it never decides fit.

Exit 0 only if every item above holds. Usage (repo root, after the PDK exists on the runner):
  python3 test/physical_fa_check.py --out physical-fa-check
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
PDK_VERSION = "8afc8346a57fe1ab7934ba5a6056ea8b43078e71"
SWAP_OLD = ".COUT(cout), .SUM(sum)"
SWAP_NEW = ".COUT(sum), .SUM(cout)"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd, timeout=None):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        class R:
            returncode = 127
            stdout = ""
            stderr = "could not run %s: %s" % (cmd[0], e)
        return R()


def find_pdk_verilog(version, pdk):
    roots = ["/home/runner/.ciel", os.path.expanduser("~/.ciel"), os.environ.get("PDK_ROOT", "")]
    found = set()
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        pattern = os.path.join(r, "**", version, pdk, "libs.ref", "sky130_fd_sc_hd", "verilog", "primitives.v")
        for prim in glob.glob(pattern, recursive=True):
            d = os.path.dirname(prim)
            model = os.path.join(d, "sky130_fd_sc_hd.v")
            if all(os.path.isfile(x) and os.path.getsize(x) > 0 for x in (prim, model)):
                found.add(os.path.realpath(d))
    if len(found) != 1:
        raise RuntimeError("expected exactly one %s/%s Verilog model directory for PDK %s, found %s"
                           % (pdk, "sky130_fd_sc_hd", version, sorted(found)))
    d = found.pop()
    return os.path.join(d, "primitives.v"), os.path.join(d, "sky130_fd_sc_hd.v")


def ensure_iverilog():
    if shutil.which("iverilog") and shutil.which("vvp"):
        return
    run(["sudo", "apt-get", "update"])
    r = run(["sudo", "apt-get", "install", "-y", "iverilog"])
    if r.returncode != 0 or not (shutil.which("iverilog") and shutil.which("vvp")):
        raise RuntimeError("iverilog is not available and could not be installed")


def simulate(tmp, tag, tb, top, rtl, models, params, log_dir, timeout):
    """Compile and run one test bench with the physical branch. Returns (compile rc, run rc, stdout)."""
    exe = os.path.join(tmp, tag)
    cmd = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DSIM", "-DUNIT_DELAY=#1", "-DPHI_FA_PHYS", "-s", top]
    cmd += ["-P%s.%s=%s" % (top, k, v) for k, v in params]
    cmd += ["-o", exe, tb, rtl] + list(models)
    c = run(cmd, timeout=600)
    with open(os.path.join(log_dir, tag + ".compile.log"), "w", encoding="utf-8") as f:
        f.write(" ".join(cmd) + "\n" + c.stdout + c.stderr)
    if c.returncode != 0:
        return c.returncode, None, ""
    r = run(["vvp", exe], timeout=timeout)
    with open(os.path.join(log_dir, tag + ".run.log"), "w", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)
    return 0, r.returncode, r.stdout


def result(stdout, key):
    found = re.findall(r"%s N=(\d+) MISMATCH=(\d+)" % key, stdout)
    return (int(found[0][0]), int(found[0][1])) if len(found) == 1 else None


def write_hex(path, words):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join("%04x" % w for w in words) + "\n")


def simulate_add(tmp, tag, add_src, models, settle, pairs, log_dir, timeout):
    """The adder (add_src + the real gf16_sig_mul10.v, technology branch) on the vector bench unit_tb.v with
    oracle expectations. Returns (compile rc, run rc, stdout)."""
    import gf16_oracle as orc
    fa, fb, fe = (os.path.join(tmp, "%s.%s.hex" % (tag, k)) for k in ("a", "b", "e"))
    write_hex(fa, [p[0] for p in pairs])
    write_hex(fb, [p[1] for p in pairs])
    write_hex(fe, [orc.add(a, b) for a, b in pairs])
    exe = os.path.join(tmp, tag)
    cmd = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DSIM", "-DUNIT_DELAY=#1", "-DPHI_FA_PHYS", "-DUNIT_ADD",
           "-s", "unit_tb", "-Punit_tb.SETTLE=%d" % settle, "-o", exe, os.path.join(HERE, "unit_tb.v"), add_src,
           os.path.join(SRC, "gf16_sig_mul10.v")] + list(models)
    c = run(cmd, timeout=600)
    with open(os.path.join(log_dir, tag + ".compile.log"), "w", encoding="utf-8") as f:
        f.write(" ".join(cmd) + "\n" + c.stdout + c.stderr)
    if c.returncode != 0:
        return c.returncode, None, ""
    r = run(["vvp", exe, "+A=" + fa, "+B=" + fb, "+E=" + fe, "+N=%d" % len(pairs)], timeout=timeout)
    with open(os.path.join(log_dir, tag + ".run.log"), "w", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)
    return 0, r.returncode, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="physical-fa-check")
    ap.add_argument("--pdk", default="sky130A")
    ap.add_argument("--pdk-version", default=PDK_VERSION)
    ap.add_argument("--settle", type=int, default=100, help="ns to wait before each comparison (simulation setting)")
    ap.add_argument("--timeout", type=int, default=3000, help="seconds per simulation run")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    problems = []
    info = {"pdk": args.pdk, "pdk_version": args.pdk_version, "settle_ns": args.settle}
    rtl = os.path.join(SRC, "gf16_sig_mul10.v")
    try:
        ensure_iverilog()
        info["iverilog"] = (run(["iverilog", "-V"]).stdout.splitlines() or ["unknown"])[0]
        prim, model = find_pdk_verilog(args.pdk_version, args.pdk)
        info.update(primitives=prim, primitives_sha256=sha256(prim), model=model, model_sha256=sha256(model),
                    rtl_sha256=sha256(rtl), tb_fa1_truth_sha256=sha256(os.path.join(HERE, "tb_fa1_truth.v")),
                    tb_sig_mul10_sha256=sha256(os.path.join(HERE, "tb_sig_mul10.v")))
        models = [prim, model]
        with tempfile.TemporaryDirectory() as tmp:
            # 1. truth cases of the PDK cell and of the wrapper
            cc, rc, out = simulate(tmp, "truth", os.path.join(HERE, "tb_fa1_truth.v"), "tb_fa1_truth", rtl,
                                   models, [], args.out, args.timeout)
            res = result(out, "FA1_TRUTH_RESULT")
            info["truth"] = {"compile_rc": cc, "run_rc": rc, "result": res}
            if not (cc == 0 and rc == 0 and res == (8, 0) and "TRUTH MISMATCH" not in out):
                problems.append("fa_1 truth cases failed or unknown: compile %s run %s result %s" % (cc, rc, res))
            # 2. all 2^20 products against the integer product, physical branch
            cc, rc, out = simulate(tmp, "product", os.path.join(HERE, "tb_sig_mul10.v"), "tb_sig_mul10", rtl,
                                   models, [("SETTLE", args.settle)], args.out, args.timeout)
            res = result(out, "SIGMUL10_RESULT")
            info["product"] = {"compile_rc": cc, "run_rc": rc, "result": res}
            if not (cc == 0 and rc == 0 and res == (1 << 20, 0)):
                problems.append("physical 2^20 product check failed or unknown: compile %s run %s result %s"
                                % (cc, rc, res))
            # 3. negative control: SUM and COUT swapped in the cell branch must be caught
            with open(rtl, encoding="utf-8") as f:
                text = f.read()
            if text.count(SWAP_OLD) != 1:
                problems.append("negative control text %r found %d times in gf16_sig_mul10.v (must be 1)"
                                % (SWAP_OLD, text.count(SWAP_OLD)))
            else:
                broken = os.path.join(tmp, "gf16_sig_mul10_swapped.v")
                with open(broken, "w", encoding="utf-8") as f:
                    f.write(text.replace(SWAP_OLD, SWAP_NEW))
                cc, rc, out = simulate(tmp, "negative", os.path.join(HERE, "tb_sig_mul10.v"), "tb_sig_mul10",
                                       broken, models, [("SETTLE", args.settle), ("ROWS", 64)], args.out, args.timeout)
                res = result(out, "SIGMUL10_RESULT")
                info["negative_control"] = {"compile_rc": cc, "run_rc": rc, "result": res}
                if not (cc == 0 and rc == 0 and res is not None and res[0] == 64 * 1024 and res[1] > 0):
                    problems.append("negative control (swapped SUM/COUT) was not caught: compile %s run %s result %s"
                                    % (cc, rc, res))
            # 4. the active adder, technology branch, against the oracle
            sys.path.insert(0, HERE)
            import add_zero_sweep
            import add_vectors
            import add_carry_check
            add_src = os.path.join(SRC, "gf16_v2_add.v")
            info.update(add_rtl_sha256=sha256(add_src), unit_tb_sha256=sha256(os.path.join(HERE, "unit_tb.v")),
                        oracle_sha256=sha256(os.path.join(HERE, "gf16_oracle.py")),
                        add_vectors_sha256=sha256(os.path.join(HERE, "add_vectors.py")))
            sets = (("add_zero", add_zero_sweep.vectors()), ("add_carry", add_vectors.carry_pairs()))
            carry_set = sets[1][1]
            for tag, pairs in sets:
                if not 0 < len(pairs) <= 262144:
                    problems.append("%s: %d vectors do not fit the bench (1..262144)" % (tag, len(pairs)))
                    continue
                cc, rc, out = simulate_add(tmp, tag, add_src, models, args.settle, pairs, args.out, args.timeout)
                res = result(out, "UNIT_RESULT add")
                info[tag] = {"compile_rc": cc, "run_rc": rc, "result": res, "expected_n": len(pairs)}
                if not (cc == 0 and rc == 0 and res == (len(pairs), 0) and "UNIT_ERROR" not in out):
                    problems.append("physical ADD %s check failed or unknown: compile %s run %s result %s (need N=%d, 0)"
                                    % (tag, cc, rc, res, len(pairs)))
            # 5. negative control of the adder's carry chain in this branch
            with open(add_src, encoding="utf-8") as f:
                atext = f.read()
            old, new = add_carry_check.SEED_MUTATION
            if atext.count(old) != 1:
                problems.append("ADD carry-seed control text %r found %d times in gf16_v2_add.v (must be 1)"
                                % (old, atext.count(old)))
            else:
                broken = os.path.join(tmp, "gf16_v2_add_seed0.v")
                with open(broken, "w", encoding="utf-8") as f:
                    f.write(atext.replace(old, new))
                cc, rc, out = simulate_add(tmp, "add_negative", broken, models, args.settle, carry_set, args.out,
                                           args.timeout)
                res = result(out, "UNIT_RESULT add")
                shown = [(int(a, 16), int(b, 16)) for a, b in add_carry_check.MISMATCH_RE.findall(out)]
                real = any(add_vectors.finite_nonzero_opposite(a, b) for a, b in shown)
                info["add_negative_control"] = {"compile_rc": cc, "run_rc": rc, "result": res,
                                                "finite_opposite_sign_mismatch": real}
                if not (cc == 0 and rc == 0 and res is not None and res[0] == len(carry_set) and res[1] > 0 and real):
                    problems.append("ADD carry-seed control was not caught: compile %s run %s result %s real %s"
                                    % (cc, rc, res, real))
    except Exception as e:  # report instead of dying silently; the artifact must explain itself
        problems.append("%s: %s" % (type(e).__name__, e))

    status = "FAIL" if problems else "PASS"
    with open(os.path.join(args.out, "physical-fa-check.json"), "w", encoding="utf-8") as f:
        json.dump({"status": status, "problems": problems, "info": info}, f, indent=2, sort_keys=True)
    with open(os.path.join(args.out, "STATUS.txt"), "w", encoding="utf-8") as f:
        f.write(status + "\n")
    lines = ["# PHYSICAL_FA_CHECK (PDK Verilog models, technology branch; NOT a layout proof, NOT a fit proof)", "",
             "Status: **%s**" % status, ""]
    for key in ("truth", "product", "negative_control", "add_zero", "add_carry", "add_negative_control"):
        if key in info:
            lines.append("- %s: %s" % (key, info[key]))
    for key in ("pdk_version", "iverilog", "primitives_sha256", "model_sha256", "rtl_sha256", "add_rtl_sha256",
                "unit_tb_sha256", "oracle_sha256", "add_vectors_sha256", "settle_ns"):
        if key in info:
            lines.append("- %s: %s" % (key, info[key]))
    if problems:
        lines += ["", "Problems:"] + ["- " + p for p in problems]
    with open(os.path.join(args.out, "PHYSICAL_FA_CHECK.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("PHYSICAL_FA_CHECK %s" % status)
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
