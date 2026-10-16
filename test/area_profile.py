#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hierarchical area DIAGNOSIS of the active design, run in CI after the official Build GDS step.

It answers one question that the flat GDS synthesis cannot: WHERE the area is. It is a DIAGNOSIS, not a
fit proof: it uses the host `yosys` (apt, a different version from the one inside the GDS flow, the
version is recorded) with a plain recipe and the real sky130 hd typical liberty that Build GDS left on
the runner. Only the official gds / precheck / gl_test jobs decide fit.

Profiles (all synthesised with the SAME recipe and the SAME liberty):
  mul_sig_csa            the carry-save 10x10 multiplier alone (inputs are free, nothing constant)
  mul_gf16_current       gf16_v2_mul with the significand multiplier flattened in, so the hidden-1 bits
                         ({1'b1, M}) really are constants (as in the chip)
  mul_gf16_949           the same for commit 949a634
  add_949, add_current   gf16_v2_add of commit 949a634 and of the current commit
  top_full_949, top_full_current       the whole top with the real MUL and ADD flattened in
  top_storage_949, top_storage_current  the top with MUL and ADD replaced by BLACKBOXES whose outputs are
                         not constant: this measures storage, multiplexers and control only; the
                         blackbox cells have no area in the liberty and are EXCLUDED from that number
                         (it is not the area of the whole chip)
Differences current - 949 for the adder, the storage/control and the full top separate the memory
change from the adder change.

Recipe per profile: read_verilog, hierarchy -check -top T, synth -top T -flatten, opt -purge, dffunmap,
dfflibmap -liberty L, abc -liberty L, opt_clean -purge, stat -liberty L. A profile that fails (yosys
error, no 'Chip area' line, area <= 0, ANY cell of unknown area or unmapped cell outside the two
allowed blackboxes of the storage profile) is reported as FAIL with no number; nothing is ever filled in
with 0, and only the FINAL `stat` report (written by `tee -o`) is parsed. Any incomplete diagnosis makes
this script exit NON-ZERO, so the step turns red; it records PASS or FAIL in STATUS.txt and prints a
GitHub ::error annotation. The upload step has `if: always()`, so the artifact is kept either way, and
this step can never turn a red Build GDS green: its status is separate.

Usage (repo root, after Build GDS): python3 test/area_profile.py --out area-profile
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

PIN949 = "949a634ad2b4d16964d571db57fbb49c456721f7"
LIB_NAME = "sky130_fd_sc_hd__tt_025C_1v80.lib"
ACTIVE = ("tt_um_trinity_nano.v", "gf16_v2_mul.v", "gf16_v2_add.v", "gf16_sig_mul10.v")
BLACKBOX = """(* blackbox *)
module gf16_v2_mul (input wire [15:0] a, input wire [15:0] b, output wire [15:0] result);
endmodule
(* blackbox *)
module gf16_v2_add (input wire [15:0] a, input wire [15:0] b, output wire [15:0] result);
endmodule
"""

problems = []
commands = []


def note(msg):
    print(msg)


def problem(msg):
    problems.append(msg)
    print("AREA_PROFILE PROBLEM:", msg)


def run(cmd, **kw):
    commands.append(" ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def in_variant(path, pdk):
    """True when path ends with .../<pdk>/libs.ref/sky130_fd_sc_hd/lib/<LIB_NAME> for EXACTLY this pdk
    variant (a path component equal to pdk, directly followed by those three components)."""
    parts = path.split(os.sep)
    for i, comp in enumerate(parts):
        if comp == pdk and parts[i + 1:i + 4] == ["libs.ref", "sky130_fd_sc_hd", "lib"]:
            return True
    return False


def find_lib(pdk):
    """The liberty of the PDK variant the official build used (pdk: sky130A). The ciel store holds both
    sky130A and sky130B under the same version, so the variant is part of the selection; the other
    variant is excluded explicitly. Still exactly ONE real non-empty file is required."""
    roots = ["/home/runner/.ciel", os.path.expanduser("~/.ciel"), os.environ.get("PDK_ROOT", "")]
    found = set()
    for r in roots:
        if r and os.path.isdir(r):
            for p in glob.glob(os.path.join(r, "**", LIB_NAME), recursive=True):
                if in_variant(p, pdk) and os.path.isfile(p) and os.path.getsize(p) > 0:
                    real = os.path.realpath(p)
                    # a sky130A path that resolves into another variant is not accepted either
                    if any(c.startswith("sky130") and c != pdk for c in real.split(os.sep)
                           if c in ("sky130A", "sky130B")):
                        continue
                    found.add(real)
    if len(found) != 1:
        raise RuntimeError("expected exactly one non-empty %s under %s/libs.ref/sky130_fd_sc_hd/lib, found %s"
                           % (LIB_NAME, pdk, sorted(found)))
    return found.pop()


def ensure_yosys():
    if not shutil.which("yosys"):
        r1 = run(["sudo", "apt-get", "update"])
        r2 = run(["sudo", "apt-get", "install", "-y", "yosys"])
        if r2.returncode != 0 or not shutil.which("yosys"):
            raise RuntimeError("could not install yosys: %s" % r2.stderr[-400:])
    v = run(["yosys", "-V"])
    return v.stdout.strip() or v.stderr.strip()


def fetch_949(out):
    """The archived 949a634 sources via git (no checkout, the working branch is not touched)."""
    d = os.path.join(out, "src949")
    os.makedirs(d, exist_ok=True)
    if run(["git", "cat-file", "-e", PIN949 + "^{commit}"]).returncode != 0:
        f = run(["git", "fetch", "--depth=1", "origin", PIN949])
        if f.returncode != 0:
            raise RuntimeError("git fetch of %s failed: %s" % (PIN949, f.stderr[-300:]))
    for name in ACTIVE:
        s = run(["git", "show", "%s:src/%s" % (PIN949, name)])
        if s.returncode != 0 or not s.stdout.strip():
            raise RuntimeError("git show %s:src/%s failed" % (PIN949, name))
        with open(os.path.join(d, name), "w") as f:
            f.write(s.stdout)
    return d


def parse_stat(text, top):
    """Parse ONLY the report written by `tee -o <file> stat -liberty L` (the final statistics), never
    the whole log, which also holds earlier generic statistics of the synth script."""
    area = None
    for m in re.finditer(r"Chip area for (?:top )?module '\\?([^']+)': ([0-9.eE+-]+)", text):
        if m.group(1) == top:
            area = float(m.group(2))
    cells = None
    m = re.search(r"^\s*(\d+)\s+(?:[0-9.eE+-]+\s+)?cells\s*$", text, re.M) \
        or re.search(r"Number of cells:\s+(\d+)", text)
    if m:
        cells = int(m.group(1))
    seq = re.search(r"of which used for sequential elements: ([0-9.eE+-]+)", text)
    unknown = sorted(set(u.lstrip("\\") for u in re.findall(r"Area for cell type (\S+) is unknown", text)))
    return area, cells, (float(seq.group(1)) if seq else None), unknown


BLACKBOX_NAMES = {"gf16_v2_add", "gf16_v2_mul"}


def profile(name, top, files, lib, out, results, excluded=None):
    """excluded is None for full/arithmetic profiles: ANY cell of unknown area or any unmapped cell is a
    FAIL with no number. For the storage profile it is the label, and the ONLY allowed unknown-area
    cells are exactly the two blackboxes gf16_v2_add and gf16_v2_mul (and both must be present)."""
    os.makedirs(os.path.join(out, "logs"), exist_ok=True)
    os.makedirs(os.path.join(out, "scripts"), exist_ok=True)
    report = os.path.join(out, "logs", name + ".stat.txt")
    script = "; ".join(
        ["read_verilog %s" % f for f in files] +
        ["hierarchy -check -top %s" % top,
         "synth -top %s -flatten" % top,
         "opt -purge", "dffunmap",
         "dfflibmap -liberty %s" % lib,
         "abc -liberty %s" % lib,
         "opt_clean -purge",
         "tee -o %s stat -liberty %s" % (report, lib)])
    with open(os.path.join(out, "scripts", name + ".ys"), "w") as f:
        f.write(script.replace("; ", "\n") + "\n")
    r = run(["yosys", "-p", script])
    with open(os.path.join(out, "logs", name + ".log"), "w") as f:
        f.write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    area, cells, seq, unknown = (None, None, None, [])
    if r.returncode == 0 and os.path.isfile(report):
        with open(report) as f:
            area, cells, seq, unknown = parse_stat(f.read(), top)
    bad = None
    if r.returncode != 0:
        bad = "yosys exit %d" % r.returncode
    elif area is None or area <= 0:
        bad = "no positive 'Chip area' for %s in the final statistics" % top
    elif excluded is None and unknown:
        bad = "cells of unknown area or unmapped cells: %s" % unknown
    elif excluded is not None and set(unknown) != BLACKBOX_NAMES:
        bad = "unknown-area cells %s are not exactly the blackboxes %s" % (unknown, sorted(BLACKBOX_NAMES))
    if bad:
        problem("profile %s FAILED (%s); no number is reported" % (name, bad))
        results[name] = {"status": "FAIL", "reason": bad}
        return
    results[name] = {"status": "OK", "top": top, "area_um2": area, "cells": cells, "sequential_um2": seq,
                     "excluded_blackbox_cells": unknown if excluded else [], "note": excluded or ""}
    note("%-24s area %12.3f um2  cells %s%s" % (name, area, cells, ("   [" + excluded + "]") if excluded else ""))


def delta(results, a, b):
    ra, rb = results.get(a, {}), results.get(b, {})
    if ra.get("status") == "OK" and rb.get("status") == "OK":
        return ra["area_um2"] - rb["area_um2"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdk", default="sky130A",
                    help="PDK variant of the official build (gds.yaml uses pdk: sky130A); sky130B is excluded")
    args = ap.parse_args()
    out = args.out
    os.makedirs(out, exist_ok=True)
    results = {}
    meta = {"pin949": PIN949}
    try:
        meta["yosys"] = ensure_yosys()
        note("host yosys: %s (NOT the version inside the GDS flow; diagnosis only)" % meta["yosys"])
        lib = find_lib(args.pdk)
        meta["pdk_variant"] = args.pdk
        with open(lib, "rb") as f:
            meta["liberty"] = {"path": lib, "bytes": os.path.getsize(lib),
                               "sha256": hashlib.sha256(f.read()).hexdigest()}
        note("liberty: %s" % lib)
        head = run(["git", "rev-parse", "HEAD"])
        meta["head"] = head.stdout.strip()
        src949 = fetch_949(out)
        with open(os.path.join(out, "bb.v"), "w") as f:
            f.write(BLACKBOX)
        bb = os.path.join(out, "bb.v")
        cur = ["src/" + n for n in ACTIVE]
        old = [os.path.join(src949, n) for n in ACTIVE]
        c = lambda n: "src/" + n
        o = lambda n: os.path.join(src949, n)
        profile("mul_sig_csa", "gf16_sig_mul10", [c("gf16_sig_mul10.v")], lib, out, results)
        profile("mul_gf16_current", "gf16_v2_mul", [c("gf16_v2_mul.v"), c("gf16_sig_mul10.v")], lib, out, results)
        profile("mul_gf16_949", "gf16_v2_mul", [o("gf16_v2_mul.v"), o("gf16_sig_mul10.v")], lib, out, results)
        profile("add_949", "gf16_v2_add", [o("gf16_v2_add.v")], lib, out, results)
        # the current adder instantiates gf16_fa1 (defined in gf16_sig_mul10.v); the 949 adder does not
        profile("add_current", "gf16_v2_add", [c("gf16_v2_add.v"), c("gf16_sig_mul10.v")], lib, out, results)
        profile("top_full_949", "tt_um_trinity_nano", old, lib, out, results)
        profile("top_full_current", "tt_um_trinity_nano", cur, lib, out, results)
        why = "MUL and ADD replaced by blackboxes: storage, multiplexers and control only; blackbox area EXCLUDED"
        profile("top_storage_949", "tt_um_trinity_nano", [bb, o("tt_um_trinity_nano.v")], lib, out, results, why)
        profile("top_storage_current", "tt_um_trinity_nano", [bb, c("tt_um_trinity_nano.v")], lib, out, results, why)
    except Exception as e:                      # diagnosis must report, never invent
        problem("%s: %s" % (type(e).__name__, e))

    deltas = {
        "add_current_minus_949": delta(results, "add_current", "add_949"),
        "top_storage_current_minus_949": delta(results, "top_storage_current", "top_storage_949"),
        "top_full_current_minus_949": delta(results, "top_full_current", "top_full_949"),
    }
    sane = None
    if all(results.get(k, {}).get("status") == "OK"
           for k in ("top_storage_current", "mul_gf16_current", "add_current", "top_full_current")):
        sane = results["top_full_current"]["area_um2"] - (results["top_storage_current"]["area_um2"]
                                                          + results["mul_gf16_current"]["area_um2"]
                                                          + results["add_current"]["area_um2"])
    meta.update({"results": results, "deltas": deltas, "full_minus_parts_current": sane,
                 "problems": problems, "commands": commands})
    with open(os.path.join(out, "area-profile.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    with open(os.path.join(out, "commands.txt"), "w") as f:
        f.write("\n".join(commands) + "\n")
    lines = ["# AREA_PROFILE (diagnosis, not a fit proof)", "",
             "Host yosys: %s. Same recipe and same liberty for every row. Liberty: %s" %
             (meta.get("yosys"), meta.get("liberty", {}).get("path")), "",
             "| profile | area um2 | cells | note |", "|---|---:|---:|---|"]
    for k, v in results.items():
        if v.get("status") == "OK":
            lines.append("| %s | %.3f | %s | %s |" % (k, v["area_um2"], v["cells"], v["note"]))
        else:
            lines.append("| %s | FAIL | - | no number reported |" % k)
    lines += ["", "| difference (current - 949a634) | um2 |", "|---|---:|"]
    for k, v in deltas.items():
        lines.append("| %s | %s |" % (k, "%.3f" % v if v is not None else "n/a (a profile failed)"))
    if sane is not None:
        lines += ["", "top_full_current - (storage + mul_gf16 + add) = %.3f um2 (cross-optimisation effects; "
                  "the three parts are synthesised separately)" % sane]
    with open(os.path.join(out, "AREA_PROFILE.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "STATUS.txt"), "w") as f:
        f.write("PASS\n" if not problems else "FAIL\n" + "\n".join(problems) + "\n")
    if problems:
        print("::error title=AREA_PROFILE diagnosis incomplete::%s" % "; ".join(problems)[:500])
        print("AREA_PROFILE FAIL: diagnosis incomplete, exiting non-zero (diagnosis only, not a fit proof)")
        return 1
    print("AREA_PROFILE PASS (complete diagnosis; host yosys, not the GDS flow's; not a fit proof)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
