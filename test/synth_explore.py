#!/usr/bin/env python3
"""Measure the supported official synthesis strategies on the SAME design, PDK and cell exclusions as the
official GDS flow. Diagnosis only: this is NOT a fit proof and never changes the physical verdict (the main
GDS job on the last SHA decides that).

It runs the LibreLane 3.0.14 built-in flow `SynthesisExploration` (Yosys.Synthesis -> OpenROAD.CheckSDCFiles ->
OpenROAD.STAPrePNR for each of AREA 0..3 and DELAY 0..4) with `src/config_merged.json`, in its own run
directory, never touching `runs/wokwi`. The built-in flow swallows a failed strategy (StepError) and can
still exit 0, so the result is rebuilt from the real step state files: one row per strategy, value or an
explicit null with the reason, never a zero for a missing value. The strategy of a row comes strictly from the
normalised name of its custom STA directory (`<n>-sta-<strategy>`; the STA config has no SYNTH_STRATEGY, that
variable belongs to Yosys only); that STA directory must have meta.step OpenROAD.STAPrePNR and a matching
`<n>-synthesis-<strategy>` directory (meta.step Yosys.Synthesis, config.SYNTH_STRATEGY equal) supplies cells and area.
A missing, duplicated or mismatching source fails the row.

Calibration has no hard-coded numbers: the baseline is read from the official Build GDS run of the same SHA
(`runs/wokwi/*-yosys-synthesis/config.json` SYNTH_STRATEGY and `state_out.json` metrics design__instance__count /
design__instance__area; exactly one such directory, positive finite values, integer count). The row of THAT SAME
strategy must reproduce it (today AREA 0; if the official config later uses another strategy, that one is
calibrated). The baseline directory is only read.

Fail-closed: exit 0 only when the flow exited 0, all nine rows are valid, the baseline is complete and the
calibration holds. Anything else exits non-zero; the nine rows are always reported (null when missing).

The container option order is required: `--docker-no-tty` before `--dockerized`.

Usage (repo root, after the official Build GDS step):
  python3 test/synth_explore.py --out synth-explore-out
  python3 test/synth_explore.py --no-run --run-dir <existing run dir> --baseline-run <copied official run> --out <dir>
"""
import argparse
import glob
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import sys

STRATEGIES = ["AREA 0", "AREA 1", "AREA 2", "AREA 3", "DELAY 0", "DELAY 1", "DELAY 2", "DELAY 3", "DELAY 4"]
KEYS = [("count", "design__instance__count"), ("area", "design__instance__area"),
        ("r2r_ws", "timing__setup_r2r__ws"), ("ws", "timing__setup__ws"), ("tns", "timing__setup__tns")]
LIBRELANE_VERSION = "3.0.14"
IMAGE = "ghcr.io/librelane/librelane:" + LIBRELANE_VERSION
OFFICIAL_RUN_DIR = os.path.join("runs", "wokwi")


def num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


STEP_DIR = re.compile(r"^(\d+)-(sta|synthesis)-(area|delay)[-_ ]*(\d)$")
STA_STEP = "OpenROAD.STAPrePNR"
SYNTH_STEP = "Yosys.Synthesis"


def parse_step_dir(name):
    """`<ordinal>-sta-<strategy>` / `<ordinal>-synthesis-<strategy>` (the flow names a step directory
    `<ordinal>-slugify(step.id)` and SynthesisExploration sets the ids `sta-<strategy>`, `synthesis-<strategy>`).
    Case, space, underscore and hyphen are tolerated; returns (kind, canonical strategy) or None."""
    m = STEP_DIR.match(name.strip().lower())
    if not m:
        return None
    strategy = "%s %s" % (m.group(3).upper(), m.group(4))
    return (m.group(2), strategy) if strategy in STRATEGIES else None


def blank_row(status, reason, step=None):
    return {"status": status, "step": step, "reason": reason,
            "count": None, "area": None, "r2r_ws": None, "ws": None, "tns": None}


def collect(run_dir):
    """One row per strategy. The strategy is taken STRICTLY from the normalised name of the custom STA directory
    (the STA config has no SYNTH_STRATEGY: that is a Yosys-only variable). The STA directory must say
    meta.step == OpenROAD.STAPrePNR; the matching synthesis directory (same strategy in its name) must say
    meta.step == Yosys.Synthesis and carry config.SYNTH_STRATEGY equal to it. Cells and area come from the
    synthesis state, slacks from the STA state; the STA count/area, when present, must agree. A missing,
    duplicated, mismatching or unreadable source makes the row failed; a missing metric stays null."""
    sources = {s: {"sta": [], "synthesis": []} for s in STRATEGIES}
    for name in sorted(os.listdir(run_dir)):
        parsed = parse_step_dir(name)
        d = os.path.join(run_dir, name)
        if parsed is None or not os.path.isdir(d):
            continue
        sources[parsed[1]][parsed[0]].append(name)
    rows, configs = {}, {}
    for s in STRATEGIES:
        sta_dirs, syn_dirs = sources[s]["sta"], sources[s]["synthesis"]
        if len(sta_dirs) != 1 or len(syn_dirs) != 1:
            rows[s] = blank_row("failed", "need exactly one STA and one synthesis directory, found STA %s synthesis %s"
                                % (sta_dirs, syn_dirs))
            continue
        sta_name, syn_name = sta_dirs[0], syn_dirs[0]
        try:
            sta_cfg = read_json(os.path.join(run_dir, sta_name, "config.json"))
            syn_cfg = read_json(os.path.join(run_dir, syn_name, "config.json"))
            sta_metrics = read_json(os.path.join(run_dir, sta_name, "state_out.json"))["metrics"]
            syn_metrics = read_json(os.path.join(run_dir, syn_name, "state_out.json"))["metrics"]
        except (OSError, ValueError, KeyError, TypeError) as e:
            rows[s] = blank_row("failed", "unreadable step files: %s" % e, sta_name)
            continue
        if not isinstance(sta_cfg, dict) or not isinstance(syn_cfg, dict) \
                or not isinstance(sta_metrics, dict) or not isinstance(syn_metrics, dict):
            rows[s] = blank_row("failed", "step files have an unexpected shape", sta_name)
            continue
        if (sta_cfg.get("meta") or {}).get("step") != STA_STEP:
            rows[s] = blank_row("failed", "%s is not an %s step" % (sta_name, STA_STEP), sta_name)
            continue
        if (syn_cfg.get("meta") or {}).get("step") != SYNTH_STEP:
            rows[s] = blank_row("failed", "%s is not a %s step" % (syn_name, SYNTH_STEP), sta_name)
            continue
        declared = syn_cfg.get("SYNTH_STRATEGY")
        if not isinstance(declared, str) or declared.strip().upper().replace("_", " ") != s:
            rows[s] = blank_row("failed", "%s declares SYNTH_STRATEGY %r, expected %r" % (syn_name, declared, s), sta_name)
            continue
        configs[s] = syn_cfg
        vals = {
            "count": num(syn_metrics.get("design__instance__count")),
            "area": num(syn_metrics.get("design__instance__area")),
            "r2r_ws": num(sta_metrics.get("timing__setup_r2r__ws")),
            "ws": num(sta_metrics.get("timing__setup__ws")),
            "tns": num(sta_metrics.get("timing__setup__tns")),
        }
        for key, metric in (("count", "design__instance__count"), ("area", "design__instance__area")):
            sta_v = num(sta_metrics.get(metric))
            if sta_v is not None and vals[key] is not None and abs(sta_v - vals[key]) > 1e-6:
                vals = {k: None for k in vals}
                rows[s] = blank_row("failed", "STA %s %s differs from synthesis %s" % (metric, sta_v, syn_name), sta_name)
                break
        else:
            missing = [k for k, v in vals.items() if v is None]
            if not missing and (vals["count"] <= 0 or vals["area"] <= 0 or not vals["count"].is_integer()):
                missing, reason = list(vals), "non-positive area/count or non-integer count"
                vals = {k: None for k in vals}
            else:
                reason = ("missing metrics: " + ", ".join(missing)) if missing else None
            rows[s] = {"status": "failed" if missing else "valid", "step": sta_name, "reason": reason}
            rows[s].update(vals)
    return rows, configs


def provenance(run_dir, configs):
    info = {"librelane_python_package": None, "image": IMAGE, "image_id": None, "exclusion_files": {}, "tmp_libs": []}
    try:
        info["librelane_python_package"] = importlib.metadata.version("librelane")
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        r = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}} {{json .RepoDigests}}", IMAGE],
                           capture_output=True, text=True, timeout=60)
        info["image_id"] = r.stdout.strip() if r.returncode == 0 else "unavailable"
    except (OSError, subprocess.SubprocessError):
        info["image_id"] = "unavailable"
    cfg = configs.get("AREA 0") or next(iter(configs.values()), {})
    for key in ("SYNTH_EXCLUDED_CELL_FILE", "PNR_EXCLUDED_CELL_FILE", "EXTRA_EXCLUDED_CELLS", "PDK_ROOT"):
        info["exclusion_files"][key] = cfg.get(key)
    for key in ("SYNTH_EXCLUDED_CELL_FILE", "PNR_EXCLUDED_CELL_FILE"):
        path = cfg.get(key)
        if isinstance(path, str) and os.path.isfile(path):
            info["exclusion_files"][key + "_sha256"] = sha256(path)
            with open(path, encoding="utf-8", errors="replace") as f:
                info["exclusion_files"][key + "_lines"] = sum(1 for _ in f)
    for lib in sorted(glob.glob(os.path.join(run_dir, "tmp", "*.lib"))):
        with open(lib, encoding="utf-8", errors="replace") as f:
            cells = sum(1 for line in f if re.match(r"\s*cell\s*\(", line))
        info["tmp_libs"].append({"file": os.path.basename(lib), "cells": cells})
    return info


def fmt(v, nd):
    return "null" if v is None else ("%.*f" % (nd, v))


def write_report(out, rows, problems, meta):
    status = "FAIL" if problems else "PASS"
    lines = ["# SYNTH_EXPLORE (official LibreLane %s SynthesisExploration; diagnosis, NOT a fit proof)" % LIBRELANE_VERSION, "",
             "Status: **%s**" % status, "",
             "| SYNTH_STRATEGY | status | cells | area um2 | worst r2r setup ns | worst setup ns | TNS ns |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for s in STRATEGIES:
        r = rows[s]
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            s, r["status"], fmt(r["count"], 0), fmt(r["area"], 3), fmt(r["r2r_ws"], 3), fmt(r["ws"], 3), fmt(r["tns"], 3)))
    base = meta.get("baseline")
    lines += ["", ("Calibration baseline (official Build GDS of this SHA, `%s`): strategy %s, area %s, %s cells; the same "
                   "strategy here must reproduce it." % (meta["baseline_run"], base["strategy"], base["area"], base["count"]))
              if base else "Calibration baseline unavailable (see problems); no calibration claim.", ""]
    if problems:
        lines += ["Problems:"] + ["- " + p for p in problems] + [""]
    lines += ["Same src/config_merged.json, same PDK and cell exclusions, run directory `%s`; `runs/wokwi` untouched." % meta["run_dir"],
              "The area is the synthesis area only. 1-tile fit is decided by the main GDS job on the last SHA, never here, "
              "even when an area is smaller than the calibration value."]
    with open(os.path.join(out, "SYNTH_EXPLORE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "synth-explore.json"), "w", encoding="utf-8") as f:
        json.dump({"status": status, "problems": problems, "rows": rows, "meta": meta}, f, indent=2, sort_keys=True)
    with open(os.path.join(out, "STATUS.txt"), "w", encoding="utf-8") as f:
        f.write(status + "\n")


def load_baseline(base_run):
    """The official Build GDS synthesis of this SHA: exactly one non-empty `*-yosys-synthesis/config.json` and its
    `state_out.json`. Returns ({strategy, count, area, dir}, None) or (None, reason). Read only, nothing is
    invented: any missing or implausible piece makes the baseline (and so the calibration) fail."""
    dirs = [d for d in glob.glob(os.path.join(base_run, "*-yosys-synthesis")) if os.path.isdir(d)]
    if len(dirs) != 1:
        return None, "expected exactly one *-yosys-synthesis directory in %s, found %d" % (base_run, len(dirs))
    cfg_path, state_path = os.path.join(dirs[0], "config.json"), os.path.join(dirs[0], "state_out.json")
    for p in (cfg_path, state_path):
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            return None, "missing or empty %s" % p
    try:
        strategy = read_json(cfg_path)["SYNTH_STRATEGY"]
        metrics = read_json(state_path)["metrics"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        return None, "unreadable baseline: %s" % e
    if strategy not in STRATEGIES:
        return None, "baseline SYNTH_STRATEGY %r is not one of the nine strategies" % (strategy,)
    count, area = num(metrics.get("design__instance__count")), num(metrics.get("design__instance__area"))
    if count is None or area is None or count <= 0 or area <= 0 or not count.is_integer():
        return None, "baseline metrics invalid (count %r, area %r)" % (metrics.get("design__instance__count"),
                                                                       metrics.get("design__instance__area"))
    return {"strategy": strategy, "count": int(count), "area": area, "dir": os.path.basename(dirs[0])}, None


def run_flow(cmd, log_path):
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        for line in proc.stdout:
            log.write(line)
            sys.stdout.write(line)
        return proc.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="synth-explore-out")
    ap.add_argument("--config", default=os.path.join("src", "config_merged.json"))
    ap.add_argument("--run-dir", default=os.path.join("runs", "synth-explore"))
    ap.add_argument("--run-tag", default="synth-explore")
    ap.add_argument("--pdk", default=os.environ.get("PDK", "sky130A"))
    ap.add_argument("--baseline-run", default=OFFICIAL_RUN_DIR,
                    help="official Build GDS run directory used as the calibration baseline (read only)")
    ap.add_argument("--no-run", action="store_true", help="validate an existing run directory only")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    problems = []
    rows = {s: {"status": "failed", "step": None, "reason": "not measured", "count": None, "area": None,
                "r2r_ws": None, "ws": None, "tns": None} for s in STRATEGIES}
    meta = {"run_dir": args.run_dir, "config": args.config, "pdk": args.pdk, "flow_exit_code": None,
            "baseline_run": args.baseline_run, "baseline": None, "no_run": args.no_run}
    # --docker-no-tty must come BEFORE --dockerized: librelane's container entry reads it before the eager
    # --dockerized option re-executes the command inside the container with only the arguments after it.
    cmd = [sys.executable, "-m", "librelane", "--docker-no-tty", "--dockerized", "--flow", "SynthesisExploration",
           "--pdk", args.pdk, "--run-tag", args.run_tag, "--force-run-dir", args.run_dir, args.config]
    meta["command"] = cmd
    with open(os.path.join(args.out, "commands.txt"), "w", encoding="utf-8") as f:
        f.write(" ".join(cmd) + "\n")

    try:
        run_abs = os.path.abspath(args.run_dir)
        official_abs = os.path.abspath(OFFICIAL_RUN_DIR)
        blocked = run_abs == official_abs or run_abs.startswith(official_abs + os.sep)
        if blocked:
            problems.append("refusing to use the official run directory %s" % OFFICIAL_RUN_DIR)
        baseline, base_problem = load_baseline(args.baseline_run)
        meta["baseline"] = baseline
        if base_problem:
            problems.append("baseline: " + base_problem)
        if not blocked and not args.no_run:
            if not os.path.isfile(args.config):
                problems.append("missing config %s" % args.config)
                blocked = True
            if os.path.exists(args.run_dir) and (not os.path.isdir(args.run_dir) or os.listdir(args.run_dir)):
                problems.append("run directory %s exists and is not an empty directory" % args.run_dir)
                blocked = True
            if baseline is None:
                blocked = True   # the baseline problem is already reported
            try:
                version = importlib.metadata.version("librelane")
                if version != LIBRELANE_VERSION:
                    problems.append("librelane %s installed, expected %s" % (version, LIBRELANE_VERSION))
                    blocked = True
            except importlib.metadata.PackageNotFoundError:
                problems.append("python package librelane is not installed for %s" % sys.executable)
                blocked = True
            if not blocked:
                # LibreLane's --force-run-dir requires an existing directory (the official project harden
                # creates runs/wokwi before calling it). Every check above passed, so create our own EMPTY one;
                # an existing directory is never removed or cleaned, and --no-run never creates anything.
                try:
                    os.makedirs(args.run_dir, exist_ok=True)
                except OSError as e:
                    problems.append("could not create run directory %s: %s" % (args.run_dir, e))
                    blocked = True
            if not blocked:
                try:
                    meta["flow_exit_code"] = run_flow(cmd, os.path.join(args.out, "synth-explore.log"))
                except OSError as e:
                    problems.append("could not start the flow: %s" % e)
                if meta["flow_exit_code"] not in (None, 0):
                    problems.append("flow exit code %s" % meta["flow_exit_code"])

        if not blocked or (args.no_run and not (run_abs == official_abs or run_abs.startswith(official_abs + os.sep))):
            if os.path.isdir(args.run_dir):
                rows, configs = collect(args.run_dir)
                meta["provenance"] = provenance(args.run_dir, configs)
                summary = os.path.join(args.run_dir, "summary.rpt")
                if os.path.isfile(summary):
                    shutil.copy(summary, os.path.join(args.out, "summary.rpt"))
                    with open(summary, encoding="utf-8", errors="replace") as f:
                        if "Failed" in f.read():
                            problems.append("summary.rpt reports a failed strategy")
                else:
                    problems.append("summary.rpt missing (the flow did not finish its table)")
                for s in STRATEGIES:
                    if rows[s]["status"] != "valid":
                        problems.append("strategy %s: %s" % (s, rows[s]["reason"]))
                if baseline is not None:
                    row = rows[baseline["strategy"]]
                    if row["status"] == "valid" and (abs(row["area"] - baseline["area"]) > 0.001
                                                     or int(row["count"]) != baseline["count"]):
                        problems.append("calibration failed: %s gave area %s / %s cells, official baseline has %s / %s" % (
                            baseline["strategy"], fmt(row["area"], 3), fmt(row["count"], 0),
                            baseline["area"], baseline["count"]))
            else:
                problems.append("run directory %s does not exist" % args.run_dir)
    except Exception as e:  # report instead of dying silently; the artifact must always explain itself
        problems.append("unexpected %s: %s" % (type(e).__name__, e))

    write_report(args.out, rows, problems, meta)
    print("SYNTH_EXPLORE %s" % ("FAIL" if problems else "PASS"))
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
