#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed Yosys audit of the ACTIVE sources (those in info.yaml / PROJECT_SOURCES).

  1. read the active files, `hierarchy -check -top tt_um_trinity_nano`, `proc; opt`:
     the statistics must exist and must contain no $mul / $div / $mod / $pow cell
     (the old CI step grep'ed the log and printed a success message when grep found nothing,
     so it could not fail; this one fails when the statistics are missing);
  2. `synth -flatten` must succeed; the cell statistics are printed for the record
     (these are NOT an area or timing claim; only the GDS run of the last SHA decides fit).
Usage (repo root): python3 test/synth_audit.py        (needs yosys; exit 0 = clean)
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_project

TOP = check_project.TOP
BAD = re.compile(r"\$(mul|div|mod|pow|divfloor|modfloor)\b")


def yosys(script):
    r = subprocess.run(["yosys", "-p", script], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def last_stat(out):
    i = out.rfind("Printing statistics")
    return out[i:] if i >= 0 else ""


def main():
    files = check_project.makefile_sources()
    if not files:
        print("SYNTH_AUDIT FAIL: no PROJECT_SOURCES")
        return 1
    paths = " ".join(os.path.join("src", f) for f in files)
    rc, out = yosys("read_verilog -I src %s; hierarchy -check -top %s; proc; opt; stat" % (paths, TOP))
    stat = last_stat(out)
    if rc != 0 or "Number of cells" not in stat and "cells" not in stat:
        print(out[-2500:])
        print("SYNTH_AUDIT FAIL: yosys did not produce statistics (rc=%d)" % rc)
        return 1
    hits = sorted(set(BAD.findall(stat)))
    if hits:
        print(stat)
        print("SYNTH_AUDIT FAIL: forbidden arithmetic cells after proc/opt: %s" % hits)
        return 1
    print("pre-synthesis: no $mul/$div/$mod/$pow cells in the active design")
    rc, out = yosys("read_verilog -I src %s; hierarchy -check -top %s; synth -flatten -top %s; stat"
                    % (paths, TOP, TOP))
    stat = last_stat(out)
    if rc != 0 or not stat:
        print(out[-2500:])
        print("SYNTH_AUDIT FAIL: synth -flatten failed (rc=%d)" % rc)
        return 1
    if BAD.search(stat):
        print(stat)
        print("SYNTH_AUDIT FAIL: forbidden arithmetic cells after synth")
        return 1
    print(stat)
    print("SYNTH_AUDIT PASS: active sources synthesise; no $mul (cell counts above are a record, not a fit claim)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
