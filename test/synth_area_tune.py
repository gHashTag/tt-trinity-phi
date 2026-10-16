#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Area-only measurement of the supported official ABC area knobs (diagnosis only; NOT timing, NOT a fit proof).

Sequential synthesis-only runs of the official LibreLane 3.0.14 (docker, `--flow Classic --to
Yosys.Synthesis`, `--docker-no-tty` BEFORE `--dockerized`) on the SAME src/config_merged.json, the same sources,
PDK, cell-exclusion union and 20 ns clock. DEFAULT mode: the 6 supported measurements (AREA 0/1/2 x AREA_USE_NF
False/True, MFS3 False). `--include-mfs3` adds the 6 MFS3=True rows (12 in total). Only three supported
configuration variables change:
    SYNTH_STRATEGY       AREA 0 | AREA 1 | AREA 2 (AREA 1 is the best strategy of the last full SYNTH9 table)
    SYNTH_ABC_USE_MFS3   False | True     (adds the `mfs3 -aemvz -I 4 -O 2` area resynthesis step; True ONLY with
                         --include-mfs3: at the official 22c run all six MFS3=True rows aborted in the upstream ABC,
                         `Abc_TtExpand ... Assertion pCut[i] == pCut0[k] failed`, yosys-abc rc 134 / LibreLane rc 2 -
                         that FAIL is recorded history, never rewritten as PASS, and not "flag unsupported in
                         general"; the abort is not masked or bypassed, the tool is not replaced)
    SYNTH_ABC_AREA_USE_NF False | True    (area mapper `&get -n; &nf -R 1000; &put` instead of `amap`)
(source: construct_abc_script-3.0.14.py). Nothing else is overridden: no linter flag, no exclusion list, no
clock, no format, no design change. Temporary configs are written next to src/config_merged.json (so `dir::`
paths resolve as in the official run), copied into the artifact, and only those files are removed afterwards.
The run directories are the script's own empty ones under runs/area-tune; runs/wokwi is only read.

Dynamic calibration: the strategy and both knob values of the CURRENT official run (runs/wokwi config) must be
one of the three strategies and two real booleans, exactly one of the SELECTED rows matches them (if the official run
uses MFS3=True and `--include-mfs3` is absent the script refuses honestly; it never flips the boolean), and that row must
reproduce the official cell count, area and per-type cell counts. Every row is also checked against the official
run's provenance (exclusion files, raw filtered library sha256, PDK, versions, Yosys creator) with the same
helpers as test/official_block_profile.py (fingerprint, compare_fp, read_probe: known library cells with finite
positive areas, positive integer counts, weighted library area equal to stat and state). The effective knob values
are read back from each step's own config.json and from the generated ABC script (`mfs3` present iff requested,
`&nf -R 1000` present iff requested), so a knob that did not take effect fails the row. A tool error, an
unsupported option or a missing metric is an explicit failed row with null numbers, never 0 and never a silent
fallback; the step exits non-zero on any incomplete table, calibration or provenance mismatch or tool error.
The tool exit code is part of EVERY row: right after a run the script writes its own small record
`PHI_TOOL_EXIT.json` (rc, command, GITHUB_SHA when set) into that run's own directory, AFTER the tool finished and
with the real rc (null when the tool could not start); a row is VALID only if that record exists with rc 0, so a
partly written stat of a failed run can never become a VALID or minimum row (it is kept only under
`raw_measurements`, the public area/cell fields are null). `--no-run` requires the same record: a missing one is a
failure (rc unknown), never a pass. A non-empty run directory still blocks the run (nothing is erased or overwritten).
The summary lists the selected rows and the minimum VALID row; that row is a candidate to measure with the full GDS,
not a winner and not a fit/timing claim.

Usage (repo root, after the official Build GDS step):
  python3 test/synth_area_tune.py --out area-tune-out
  python3 test/synth_area_tune.py --no-run --runs-root <dir with the run dirs> [--include-mfs3] --baseline-run <runs/wokwi copy> \
      [--path-map OLD=NEW] --out <dir>
"""
import argparse
import glob
import importlib.metadata
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import official_block_profile as obp  # noqa: E402
import synth_explore as se  # noqa: E402

DESIGN = "tt_um_trinity_nano"
STRATEGIES = ("AREA 0", "AREA 1", "AREA 2")
# Default matrix: the 6 supported measurements (MFS3 False). The 6 MFS3=True rows are only run with --include-mfs3:
# at the official 22c run every one of them ended in the upstream ABC assertion (yosys-abc rc 134, "Abc_TtExpand ...
# Assertion pCut[i] == pCut0[k] failed", LibreLane rc 2), so they are kept as a reproducible, expected-FAIL experiment.
ROWS_SUPPORTED = [(s, False, n) for s in STRATEGIES for n in (False, True)]
ROWS_MFS3 = [(s, True, n) for s in STRATEGIES for n in (False, True)]
EXIT_FILE = "PHI_TOOL_EXIT.json"
RAW_KEYS = ("cells_total", "cells_lib", "area", "sequential_area", "state_count", "state_area", "cells_by_type")


def write_exit_file(run_dir, rc, cmd):
    """The script's OWN small record of the tool exit, written AFTER the tool finished (never before, never faked)."""
    data = {"rc": rc, "command": cmd, "source_sha": os.environ.get("GITHUB_SHA"), "written_after_run": True}
    with open(os.path.join(run_dir, EXIT_FILE), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_exit_file(run_dir):
    """(True, None) only for an existing record with rc == 0; a missing/unknown/non-zero rc is a failure."""
    path = os.path.join(run_dir, EXIT_FILE)
    try:
        data = se.read_json(path)
    except (OSError, ValueError) as e:
        return False, "tool exit record %s missing or unreadable (%s): rc unknown" % (EXIT_FILE, e)
    rc = data.get("rc") if isinstance(data, dict) else None
    if isinstance(rc, bool) or not isinstance(rc, int):
        return False, "tool exit code unknown (%r)" % (rc,)
    if rc != 0:
        return False, "tool exit code %d" % rc
    sha_here, sha_rec = os.environ.get("GITHUB_SHA"), data.get("source_sha")
    if sha_here and sha_rec and sha_here != sha_rec:
        return False, "tool exit record is from another source SHA (%s, now %s)" % (sha_rec, sha_here)
    return True, None


def row_name(strategy, mfs3, nf):
    return "%s_mfs3-%d_nf-%d" % (strategy.replace(" ", "").lower(), int(mfs3), int(nf))


def step_dir(run_dir):
    dirs = [d for d in glob.glob(os.path.join(run_dir, "*-yosys-synthesis")) if os.path.isdir(d)]
    return dirs[0] if len(dirs) == 1 else None


def read_flags(run_dir):
    """(strategy, mfs3, nf, abc script text) of a run's single synthesis step, or (None, reason)."""
    d = step_dir(run_dir)
    if d is None:
        return None, "expected exactly one *-yosys-synthesis directory in %s" % run_dir
    try:
        cfg = se.read_json(os.path.join(d, "config.json"))
    except (OSError, ValueError) as e:
        return None, "unreadable config.json: %s" % e
    strategy, mfs3, nf = cfg.get("SYNTH_STRATEGY"), cfg.get("SYNTH_ABC_USE_MFS3"), cfg.get("SYNTH_ABC_AREA_USE_NF")
    if strategy not in STRATEGIES or not isinstance(mfs3, bool) or not isinstance(nf, bool):
        return None, "unknown strategy or non-boolean knobs: %r %r %r" % (strategy, mfs3, nf)
    script = os.path.join(d, re.sub(r"\s+", "_", strategy) + ".abc")
    try:
        with open(script, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return None, "ABC script %s unreadable: %s" % (script, e)
    return (strategy, mfs3, nf, text), None


def per_type(run_dir):
    d = step_dir(run_dir)
    if d is None:
        return None
    try:
        stat = se.read_json(os.path.join(d, "reports", "stat.json"))
        return {t.lstrip("\\"): n for t, n in stat["modules"]["\\" + DESIGN]["num_cells_by_type"].items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def fmt(v, nd=3):
    return "null" if v is None else ("%.*f" % (nd, v))


def write_reports(out, rows, rows_list, problems, meta):
    status = "FAIL" if problems else "PASS"
    valid = [r for r in rows.values() if r["status"] == "valid"]
    best = [r["name"] for r in valid if r["area"] == min(v["area"] for v in valid)] if valid else []
    meta["minimum_valid_rows"] = best
    lines = ["# AREA_TUNE (official LibreLane %s, synthesis only; area-only diagnosis, NOT timing, NOT a fit proof)" % se.LIBRELANE_VERSION,
             "", "Status: **%s**" % status, "",
             "| row | strategy | MFS3 | AREA_USE_NF | status | library cells | area um2 | vs official baseline | note |",
             "|---|---|---|---|---|---:|---:|---:|---|"]
    base = meta.get("baseline")
    for (s, m, n) in rows_list:
        r = rows[row_name(s, m, n)]
        delta = None if (r["area"] is None or not base) else r["area"] - base["area"]
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], s, m, n, r["status"], "null" if r["cells_lib"] is None else r["cells_lib"], fmt(r["area"]),
            fmt(delta), r["reason"] or ("calibration row" if r["name"] == meta.get("calibration_row") else "")))
    key = meta.get("baseline_key")
    lines += ["", ("Official baseline (current `%s`): %s, MFS3 %s, AREA_USE_NF %s -> %s cells, %s um2; calibration row `%s`." % (
        meta["baseline_run"], key[0], key[1], key[2], base["count"], base["area"], meta.get("calibration_row"))) if key and base
        else "Official baseline unavailable (see problems).",
        "Minimum VALID row(s): %s. This is a candidate for the full GDS, not a winner; timing and 1-tile fit are decided by the "
        "main GDS and the later gate-level and precheck jobs on the latest SHA only." % (", ".join(best) or "none")]
    if not meta.get("include_mfs3"):
        lines += ["", "MFS3=True rows were NOT run (default mode: %d supported rows). At the official 22c run all six ended in the "
                  "upstream ABC assertion `Abc_TtExpand ... pCut[i] == pCut0[k]` (yosys-abc rc 134, LibreLane rc 2): a recorded "
                  "FAIL, not a PASS and not an unsupported flag in general; `--include-mfs3` reproduces it and is expected to fail "
                  "on that tool." % len(rows_list)]
    if problems:
        lines += ["", "Problems:"] + ["- " + p for p in problems]
    with open(os.path.join(out, "AREA_TUNE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "area-tune.json"), "w", encoding="utf-8") as f:
        json.dump({"status": status, "problems": problems, "rows": rows, "meta": meta}, f, indent=2, sort_keys=True)
    with open(os.path.join(out, "STATUS.txt"), "w", encoding="utf-8") as f:
        f.write(status + "\n")


def blank(name, strategy, mfs3, nf, reason):
    row = obp.failed_row(reason)
    row.update(name=name, requested={"strategy": strategy, "mfs3": mfs3, "nf": nf})
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="area-tune-out")
    ap.add_argument("--config", default=os.path.join("src", "config_merged.json"))
    ap.add_argument("--runs-root", default=os.path.join("runs", "area-tune"))
    ap.add_argument("--pdk", default=os.environ.get("PDK", "sky130A"))
    ap.add_argument("--baseline-run", default=se.OFFICIAL_RUN_DIR)
    ap.add_argument("--path-map", action="append", default=[], metavar="OLD=NEW")
    ap.add_argument("--no-run", action="store_true", help="validate existing run directories only")
    ap.add_argument("--include-mfs3", action="store_true",
                    help="also run the 6 MFS3=True rows (expected to abort in the upstream ABC on this tool; still FAIL)")
    args = ap.parse_args()
    rows_list = list(ROWS_SUPPORTED) + (list(ROWS_MFS3) if args.include_mfs3 else [])

    os.makedirs(args.out, exist_ok=True)
    problems, created = [], []
    path_map = []
    for item in args.path_map:
        if "=" not in item or not item.split("=", 1)[0]:
            problems.append("--path-map %r must be OLD=NEW" % item)
        else:
            path_map.append(tuple(item.split("=", 1)))
    rows = {row_name(*r): blank(row_name(*r), *r, "not measured") for r in rows_list}
    meta = {"config": args.config, "runs_root": args.runs_root, "pdk": args.pdk, "baseline_run": args.baseline_run,
            "baseline": None, "baseline_key": None, "calibration_row": None, "commands": {}, "exit_codes": {},
            "no_run": args.no_run, "path_map": [list(p) for p in path_map], "include_mfs3": args.include_mfs3,
            "rows": [row_name(*r) for r in rows_list]}
    refused = blocked = False
    try:
        runs_abs, official_abs = os.path.abspath(args.runs_root), os.path.abspath(se.OFFICIAL_RUN_DIR)
        refused = blocked = runs_abs == official_abs or runs_abs.startswith(official_abs + os.sep)
        if refused:
            problems.append("refusing to use the official run directory %s as a probe directory" % se.OFFICIAL_RUN_DIR)
        baseline, bp = se.load_baseline(args.baseline_run)
        meta["baseline"] = baseline
        if bp:
            problems.append("baseline: " + bp)
        flags, fp_reason = read_flags(args.baseline_run)
        key = None
        if flags is None:
            problems.append("baseline knobs: " + fp_reason)
        else:
            key = flags[:3]
            meta["baseline_key"] = list(key)
            meta["calibration_row"] = row_name(*key)
            if key not in rows_list:
                # never switch the boolean automatically to make the calibration possible: refuse honestly
                problems.append("the official run uses SYNTH_ABC_USE_MFS3=%s, which is not in the selected rows; rerun with "
                                "--include-mfs3 (the knob is never changed automatically)" % key[1])
                key = None
        if not blocked and not args.no_run:
            if baseline is None or key is None:
                blocked = True
            if not os.path.isfile(args.config):
                problems.append("missing config %s" % args.config)
                blocked = True
            try:
                version = importlib.metadata.version("librelane")
                if version != se.LIBRELANE_VERSION:
                    problems.append("librelane %s installed, expected %s" % (version, se.LIBRELANE_VERSION))
                    blocked = True
            except importlib.metadata.PackageNotFoundError:
                problems.append("python package librelane is not installed for %s" % sys.executable)
                blocked = True
            for (s, m, n) in rows_list:
                rd = os.path.join(args.runs_root, row_name(s, m, n))
                if os.path.exists(rd) and (not os.path.isdir(rd) or os.listdir(rd)):
                    problems.append("run directory %s exists and is not an empty directory" % rd)
                    blocked = True
            if not blocked:
                base_cfg = se.read_json(args.config)
                if base_cfg.get("DESIGN_NAME") != DESIGN:
                    problems.append("config DESIGN_NAME is %r, expected %s" % (base_cfg.get("DESIGN_NAME"), DESIGN))
                    blocked = True
            if not blocked:
                cfg_dir = os.path.dirname(os.path.abspath(args.config))
                os.makedirs(os.path.join(args.out, "configs"), exist_ok=True)
                for (s, m, n) in rows_list:
                    name = row_name(s, m, n)
                    cfg = dict(base_cfg, SYNTH_STRATEGY=s, SYNTH_ABC_USE_MFS3=m, SYNTH_ABC_AREA_USE_NF=n)
                    with tempfile.NamedTemporaryFile("w", dir=cfg_dir, prefix="phi_tune_", suffix=".json", delete=False,
                                                     encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2)
                        path = f.name
                    created.append(path)
                    shutil.copy(path, os.path.join(args.out, "configs", name + ".json"))
                    rd = os.path.join(args.runs_root, name)
                    os.makedirs(rd, exist_ok=True)   # --force-run-dir needs an existing (here: our own empty) directory
                    cmd = [sys.executable, "-m", "librelane", "--docker-no-tty", "--dockerized", "--flow", "Classic",
                           "--to", obp.SYNTH_STEP, "--pdk", args.pdk, "--run-tag", "tune-" + name, "--force-run-dir", rd,
                           os.path.relpath(path)]
                    meta["commands"][name] = cmd
                    try:
                        rc = se.run_flow(cmd, os.path.join(args.out, name + ".log"))
                    except OSError as e:
                        rc = None
                        problems.append("%s: could not start the flow: %s" % (name, e))
                    meta["exit_codes"][name] = rc
                    try:
                        write_exit_file(rd, rc, cmd)       # after the run, with the real rc (null = unknown)
                    except OSError as e:
                        problems.append("%s: could not write %s: %s" % (name, EXIT_FILE, e))
                    if rc != 0:
                        problems.append("%s: tool exit code %s" % (name, rc))
                with open(os.path.join(args.out, "commands.txt"), "w", encoding="utf-8") as f:
                    for name, cmd in meta["commands"].items():
                        f.write(" ".join(cmd) + "\n")

        if not refused and (not blocked or args.no_run):
            off_fp, _, off_problems = obp.fingerprint(args.baseline_run, path_map)
            meta["provenance_official"] = off_fp
            problems += ["official provenance: " + p for p in off_problems]
            for (s, m, n) in rows_list:
                name = row_name(s, m, n)
                rd = os.path.join(args.runs_root, name)
                fp, table, fpp = obp.fingerprint(rd, path_map)
                row = obp.read_probe(rd, DESIGN, False, table)
                row.update(name=name, requested={"strategy": s, "mfs3": m, "nf": n})
                reasons = [] if row["status"] == "valid" else [row["reason"]]
                exit_ok, exit_why = read_exit_file(rd)      # rc is part of EVERY row: missing or non-zero = failed
                if not exit_ok:
                    reasons.append(exit_why)
                reasons += ["provenance: " + p for p in fpp]
                got, why = read_flags(rd)
                if got is None:
                    reasons.append("knobs: " + why)
                else:
                    if got[:3] != (s, m, n):
                        reasons.append("effective knobs %s differ from the requested %s" % (got[:3], (s, m, n)))
                    if ("mfs3" in got[3]) != m or ("&nf -R 1000" in got[3]) != n:
                        reasons.append("the generated ABC script does not reflect MFS3=%s / AREA_USE_NF=%s" % (m, n))
                if fp is not None and off_fp is not None:
                    reasons += ["provenance: " + d for d in obp.compare_fp(off_fp, fp)]
                elif off_fp is None:
                    reasons.append("provenance: official fingerprint unavailable")
                if reasons:    # not VALID: public metrics are null; whatever was measured stays only as raw_measurements
                    row["raw_measurements"] = {k: row.get(k) for k in RAW_KEYS}
                    for k in RAW_KEYS:
                        row[k] = None
                    row["status"], row["reason"] = "failed", "; ".join(r for r in reasons if r)
                rows[name] = row
                if row["status"] != "valid":
                    problems.append("%s: %s" % (name, row["reason"]))
            if baseline is not None and key is not None:
                cal = rows[row_name(*key)]
                if cal["status"] != "valid":
                    problems.append("calibration failed: the row %s that matches the official run is not valid" % cal["name"])
                else:
                    if cal["cells_total"] != baseline["count"] or abs(cal["area"] - baseline["area"]) > 0.001:
                        problems.append("calibration failed: row %s gave %s cells / %s um2, official run %s cells / %s um2" % (
                            cal["name"], cal["cells_total"], fmt(cal["area"]), baseline["count"], baseline["area"]))
                    base_types = per_type(args.baseline_run)
                    if base_types is None or base_types != cal["cells_by_type"]:
                        problems.append("calibration failed: per-type cell counts of row %s differ from (or the official run lacks) the "
                                        "official per-type cell counts" % cal["name"])
    except Exception as e:  # report instead of dying silently; the artifact must explain itself
        problems.append("unexpected %s: %s" % (type(e).__name__, e))
    finally:
        for path in created:      # only the files this run created, already copied into the artifact
            try:
                os.remove(path)
            except OSError:
                pass
    write_reports(args.out, rows, rows_list, problems, meta)
    print("AREA_TUNE %s" % ("FAIL" if problems else "PASS"))
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
