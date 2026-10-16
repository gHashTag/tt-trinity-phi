#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Block area profile in the OFFICIAL synthesis environment (diagnosis only; NOT a fit proof).

Five synthesis-only measurements with the official LibreLane 3.0.14 (same docker image, same PDK, same cell
exclusion union as the Build GDS step; `--flow Classic --to Yosys.Synthesis`, so nothing reaches SDC/STA and no
timing is invented for the clock-less probes):
  full     the unchanged src/config_merged.json: the calibration. It must reproduce the strategy, cell count,
           area and per-type cell counts of the CURRENT official run (runs/wokwi, read only, never hard-coded).
  mul      DESIGN_NAME gf16_v2_mul (gf16_v2_mul.v + gf16_sig_mul10.v).
  add      DESIGN_NAME gf16_v2_add (gf16_v2_add.v + gf16_sig_mul10.v for the full-adder wrapper gf16_fa1).
  add_norm14  DESIGN_NAME gf16_add_norm14, the normaliser module that already exists inside the active
           gf16_v2_add.v (same file, nothing extracted; gf16_sig_mul10.v only resolves gf16_fa1). Policy: specs/physical/gf16_dot4_addnorm_probe.t27. It is
           synthesised alone, so it is NOT a share of `add`: never subtract it from add or sum it towards full.
  storage  the real tt_um_trinity_nano with gf16_v2_mul and gf16_v2_add replaced by temporary black boxes that
           have their real port lists (parsed from the real sources); the arithmetic files are left out. The
           black-box instances are EXCLUDED from the area explicitly and reported as such, never as zero area
           and never as unknown area; exactly these two black boxes (one instance each) are allowed, any other
           cell whose area is unknown fails the probe.
The probes cross optimisation boundaries differently from the full design, so their areas are NOT additive and
must not be read as a physical partition of the full area.
Temporary configs and the black-box file are written next to src/config_merged.json (so the `dir::` paths
resolve as in the official run), copied into the artifact, and only those files created by this run are removed.
No exclusion list, strategy, density or defines are overridden (`__pnr__` for the cell branch stays). Existing
directories are never removed; the run directories are the script's own empty ones under runs/block-profile.
`--docker-no-tty` is placed BEFORE `--dockerized` (the container entry reads it first).

Provenance (official run and every probe, from that run's single *-yosys-synthesis step, nothing else is scanned):
  * extra.json `libs_synth` (the filtered libraries the mapper really read) and `blackbox_models` (the original
    PDK library): each file must exist on this host, be non-empty and unique; its sha256 is recorded, and for
    libs_synth the exact (cell name -> area) table is parsed. Every cell needs a finite positive area. The
    tables of the official run and of each probe must be IDENTICAL, and so must the raw sha256 of the filtered
    library (its timing functions steer the mapper too, so equal names and areas are not enough; the random
    file names do not matter, the content does, and a mismatch is a FAIL);
  * config.json: PDK == sky130A, PDK_ROOT contains the pinned PDK version, STD_CELL_LIBRARY, EXTRA_EXCLUDED_CELLS
    (exact value), SYNTH_EXCLUDED_CELL_FILE and PNR_EXCLUDED_CELL_FILE (the keys must exist; a configured file
    must exist and be non-empty, its sha256 and line count are recorded and compared), meta.librelane_version;
  * stat.json `creator` (the real Yosys version) and the docker image id.
Missing fields are never "equal because both are missing", and unavailable provenance is a problem, not a PASS:
on artifacts downloaded to another host the recorded absolute paths do not exist, so `--no-run` reports an
explicit FAIL there unless the paths are mapped explicitly with `--path-map OLD=NEW` (recorded in the report).

Each probe row is checked against its own filtered table: every library cell type needs a finite positive area,
all counts are positive integers, the weighted sum must equal the stat area and the state area (tolerance
0.01 um2), and a type name that is not in the table is "unknown area" (no name is accepted by prefix).

Fail-closed: exit 0 only when the tool exits 0 for every probe, every row is valid, the calibration matches the
current official run, and the provenance matches. Missing values stay null. Nothing here decides fit.

Usage (repo root, after the official Build GDS step):
  python3 test/official_block_profile.py --out block-profile-out
  python3 test/official_block_profile.py --no-run --runs-root <dir with full/mul/add/add_norm14/storage> --baseline-run <runs/wokwi copy> \
      [--path-map /home/runner/work/tt-trinity-phi/tt-trinity-phi=<local root>] --out <dir>
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
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, HERE)
import synth_explore as se  # noqa: E402  (shared helpers: baseline, flow runner, json/number helpers)

PROBES = ("full", "mul", "add", "add_norm14", "storage")
TOP = "tt_um_trinity_nano"
SYNTH_STEP = "Yosys.Synthesis"
BB_MODULES = ("gf16_v2_mul", "gf16_v2_add")
EXPECTED_PORTS = {("input", 15, 0, "a"), ("input", 15, 0, "b"), ("output", 15, 0, "result")}
NORM_PORTS = {("input", 13, 0, "x"), ("output", 13, 0, "norm"), ("output", 3, 0, "lz")}
PDK_VERSION = "8afc8346a57fe1ab7934ba5a6056ea8b43078e71"
REQUIRED_CFG = ("PDK", "PDK_ROOT", "STD_CELL_LIBRARY", "SYNTH_EXCLUDED_CELL_FILE", "PNR_EXCLUDED_CELL_FILE",
                "EXTRA_EXCLUDED_CELLS")
AREA_TOL = 0.01
FILES = {
    "mul": ("gf16_v2_mul", ["gf16_v2_mul.v", "gf16_sig_mul10.v"]),
    # the adder's significand sum instantiates gf16_fa1, which is defined in gf16_sig_mul10.v
    "add": ("gf16_v2_add", ["gf16_v2_add.v", "gf16_sig_mul10.v"]),
    # the existing normaliser module of the active adder file, synthesised alone (no new RTL module); the
    # helper file only resolves gf16_fa1 of the unused adder module for the linter, synthesis keeps only the top
    "add_norm14": ("gf16_add_norm14", ["gf16_v2_add.v", "gf16_sig_mul10.v"]),
}


def probe_design(name):
    """DESIGN_NAME every probe is validated against; one table for config writing and for reading."""
    return TOP if name in ("full", "storage") else FILES[name][0]


def probe_config(base_cfg, name, bb_file=None):
    """Temporary config of one synthesised probe: the official config with ONLY DESIGN_NAME and VERILOG_FILES
    replaced (the full probe uses the official file itself and never passes through here)."""
    if name == "full":
        raise ValueError("the full probe uses the unmodified official config")
    if name == "storage":
        if not bb_file:
            raise ValueError("the storage probe needs the black-box file")
        files = ["dir::%s.v" % TOP, "dir::" + os.path.basename(bb_file)]
    else:
        files = ["dir::" + n for n in FILES[name][1]]
    return dict(base_cfg, DESIGN_NAME=probe_design(name), VERILOG_FILES=files)


def failed_row(reason, **extra):
    row = {"status": "failed", "reason": reason, "strategy": None, "cells_total": None, "cells_lib": None,
           "area": None, "sequential_area": None, "bb_instances": None, "state_count": None,
           "state_area": None, "cells_by_type": None, "step": None, "creator": None}
    row.update(extra)
    return row


def sha256_file(path):
    return se.sha256(path)


def apply_map(path, path_map):
    for old, new in path_map:
        if path == old or path.startswith(old.rstrip("/") + "/"):
            return new.rstrip("/") + path[len(old.rstrip("/")):]
    return path


def parse_lib(path):
    """(cell name -> area) of one Liberty file; the cell-level `area` is the first one after `cell (...)`."""
    table, cur, bad = {}, None, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"\s*cell\s*\(\s*\"?([^\")\s]+)\"?\s*\)", line)
            if m:
                cur = m.group(1)
                if cur in table:
                    bad.append("cell %s appears twice" % cur)
                table[cur] = None
                continue
            m = re.match(r"\s*area\s*:\s*([0-9.eE+-]+)\s*;", line)
            if m and cur is not None and table.get(cur) is None:
                try:
                    table[cur] = se.num(float(m.group(1)))
                except ValueError:
                    table[cur] = None
    if not table:
        bad.append("no cells found")
    bad += ["cell %s has no finite positive area" % c for c, a in table.items() if a is None or a <= 0]
    return table, bad


def table_digest(table):
    return hashlib.sha256("\n".join("%s=%.6f" % (c, table[c]) for c in sorted(table)).encode()).hexdigest()


def docker_image_id():
    if not shutil.which("docker"):
        return None
    try:
        r = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}} {{json .RepoDigests}}", se.IMAGE],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def fingerprint(run_dir, path_map):
    """Provenance of ONE run from its single *-yosys-synthesis step. Returns (fp, table, problems)."""
    problems = []
    dirs = [d for d in glob.glob(os.path.join(run_dir, "*-yosys-synthesis")) if os.path.isdir(d)]
    if len(dirs) != 1:
        return None, None, ["expected exactly one *-yosys-synthesis directory in %s, found %d" % (run_dir, len(dirs))]
    d = dirs[0]
    try:
        cfg = se.read_json(os.path.join(d, "config.json"))
        extra = se.read_json(os.path.join(d, "extra.json"))
        stat = se.read_json(os.path.join(d, "reports", "stat.json"))
    except (OSError, ValueError) as e:
        return None, None, ["unreadable provenance files in %s: %s" % (d, e)]
    if not isinstance(cfg, dict) or not isinstance(extra, dict) or not isinstance(stat, dict):
        return None, None, ["provenance files have an unexpected shape in %s" % d]
    fp = {"step": os.path.basename(d), "libs": [], "blackbox_models": [], "exclusion": {}, "path_map": [list(p) for p in path_map]}
    for k in REQUIRED_CFG:
        if k not in cfg:
            problems.append("config.json has no %s" % k)
    if (cfg.get("meta") or {}).get("step") != SYNTH_STEP:
        problems.append("config.json meta.step is not %s" % SYNTH_STEP)
    if (cfg.get("meta") or {}).get("librelane_version") != se.LIBRELANE_VERSION:
        problems.append("librelane_version %r, expected %s" % ((cfg.get("meta") or {}).get("librelane_version"), se.LIBRELANE_VERSION))
    if cfg.get("PDK") != "sky130A":
        problems.append("PDK is %r, expected sky130A" % cfg.get("PDK"))
    if not isinstance(cfg.get("PDK_ROOT"), str) or PDK_VERSION not in cfg["PDK_ROOT"]:
        problems.append("PDK_ROOT %r does not contain the pinned PDK %s" % (cfg.get("PDK_ROOT"), PDK_VERSION))
    if cfg.get("STD_CELL_LIBRARY") != "sky130_fd_sc_hd":
        problems.append("STD_CELL_LIBRARY is %r" % cfg.get("STD_CELL_LIBRARY"))
    fp["config"] = {k: cfg.get(k) for k in ("PDK", "PDK_ROOT", "STD_CELL_LIBRARY", "EXTRA_EXCLUDED_CELLS")}
    fp["librelane_version"] = (cfg.get("meta") or {}).get("librelane_version")
    creator = stat.get("creator")
    if not isinstance(creator, str) or not creator.strip():
        problems.append("stat.json has no creator (Yosys version)")
    fp["creator"] = creator
    image = docker_image_id()
    if image is None:
        problems.append("docker image id unavailable (container provenance)")
    fp["image_id"] = image

    def listed(key):
        v = extra.get(key)
        if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v) or len(set(v)) != len(v):
            problems.append("extra.json %s must be a non-empty list of unique paths, got %r" % (key, v))
            return []
        return v

    table = None
    for p in listed("libs_synth"):
        real = apply_map(p, path_map)
        if not os.path.isfile(real) or os.path.getsize(real) == 0:
            problems.append("filtered library %s is not available on this host (mapped: %s)" % (p, real))
            continue
        t, bad = parse_lib(real)
        problems += ["%s: %s" % (os.path.basename(p), b) for b in bad]
        if table is not None:
            problems.append("more than one filtered library is not supported")
        table = t
        fp["libs"].append({"recorded_path": p, "sha256": sha256_file(real), "cells": len(t), "table_sha256": table_digest(t) if not bad else None})
    for p in listed("blackbox_models"):
        real = apply_map(p, path_map)
        if not os.path.isfile(real) or os.path.getsize(real) == 0:
            problems.append("blackbox model library %s is not available on this host (mapped: %s)" % (p, real))
            continue
        fp["blackbox_models"].append({"recorded_path": p, "sha256": sha256_file(real)})
    for key in ("SYNTH_EXCLUDED_CELL_FILE", "PNR_EXCLUDED_CELL_FILE"):
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            real = apply_map(v, path_map)
            if not os.path.isfile(real) or os.path.getsize(real) == 0:
                problems.append("%s %s is configured but not available non-empty on this host (mapped: %s)" % (key, v, real))
                continue
            with open(real, encoding="utf-8", errors="replace") as f:
                lines = sum(1 for _ in f)
            fp["exclusion"][key] = {"recorded_path": v, "sha256": sha256_file(real), "lines": lines}
        elif v is None or v == "":
            fp["exclusion"][key] = None
        else:
            problems.append("%s has an unexpected value %r" % (key, v))
    return (None if problems else fp), (None if problems else table), problems


def compare_fp(official, probe):
    """Differences between the official run's provenance and a probe's (empty list = same)."""
    diffs = []
    for k in ("config", "librelane_version", "creator"):
        if official[k] != probe[k]:
            diffs.append("%s differs: official %r, probe %r" % (k, official[k], probe[k]))
    for key in official["exclusion"].keys() | probe["exclusion"].keys():
        a, b = official["exclusion"].get(key), probe["exclusion"].get(key)
        strip = lambda x: None if x is None else (x["recorded_path"], x["sha256"], x["lines"])
        if strip(a) != strip(b):
            diffs.append("%s differs between the official run and the probe" % key)
    if [x["sha256"] for x in official["blackbox_models"]] != [x["sha256"] for x in probe["blackbox_models"]]:
        diffs.append("original PDK library (blackbox_models) sha256 differs")
    ot, pt = [x["table_sha256"] for x in official["libs"]], [x["table_sha256"] for x in probe["libs"]]
    if ot != pt:
        diffs.append("filtered library (cell name, area) table differs from the official run")
    # The timing functions of the library steer the mapper too, so equal names and areas are not enough:
    # the raw bytes of the filtered library must be identical (random file names do not matter, content does).
    if [x["sha256"] for x in official["libs"]] != [x["sha256"] for x in probe["libs"]]:
        diffs.append("raw sha256 of the filtered library differs from the official run")
    return diffs


def ports_of(path, module, expected=EXPECTED_PORTS):
    with open(path, encoding="utf-8") as f:
        text = re.sub(r"//[^\n]*", "", f.read())
    m = re.search(r"\bmodule\s+%s\s*\((.*?)\)\s*;" % module, text, re.S)
    if not m:
        raise RuntimeError("module %s header not found in %s" % (module, path))
    found = {(d, int(hi), int(lo), n) for d, hi, lo, n in
             re.findall(r"\b(input|output)\s+(?:wire\s+|reg\s+)*\[(\d+):(\d+)\]\s*(\w+)", m.group(1))}
    if found != expected:
        raise RuntimeError("unexpected ports of %s: %s" % (module, sorted(found)))
    return found


def blackbox_text():
    parts = ["// Temporary probe file written by test/official_block_profile.py. NOT part of the design.",
             "// Black boxes with the real port lists of gf16_v2_mul / gf16_v2_add (checked against src/).",
             "// verilator lint_off UNDRIVEN", "// verilator lint_off UNUSED", ""]
    for module in BB_MODULES:
        ports_of(os.path.join(SRC, module + ".v"), module)
        parts += ["(* blackbox *)", "module %s (" % module, "    input  wire [15:0] a,", "    input  wire [15:0] b,",
                  "    output wire [15:0] result", ");", "endmodule", ""]
    parts += ["// verilator lint_on UNUSED", "// verilator lint_on UNDRIVEN", ""]
    return "\n".join(parts)


def is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def read_probe(run_dir, design, allow_bb, table):
    """One row from the probe's single *-yosys-synthesis step, validated against its own filtered cell table."""
    dirs = [d for d in glob.glob(os.path.join(run_dir, "*-yosys-synthesis")) if os.path.isdir(d)]
    if len(dirs) != 1:
        return failed_row("expected exactly one *-yosys-synthesis directory in %s, found %d" % (run_dir, len(dirs)))
    d = dirs[0]
    try:
        cfg = se.read_json(os.path.join(d, "config.json"))
        metrics = se.read_json(os.path.join(d, "state_out.json"))["metrics"]
        stat = se.read_json(os.path.join(d, "reports", "stat.json"))
        with open(os.path.join(d, "reports", "stat.rpt"), encoding="utf-8", errors="replace") as f:
            rpt = f.read()
    except (OSError, ValueError, KeyError, TypeError) as e:
        return failed_row("unreadable probe files: %s" % e, step=os.path.basename(d))
    step = os.path.basename(d)
    if (cfg.get("meta") or {}).get("step") != SYNTH_STEP or cfg.get("DESIGN_NAME") != design:
        return failed_row("%s is not the %s step of %s" % (step, SYNTH_STEP, design), step=step)
    strategy = cfg.get("SYNTH_STRATEGY")
    creator = stat.get("creator")
    module = (stat.get("modules") or {}).get("\\" + design)
    if not isinstance(module, dict):
        return failed_row("stat.json has no module %s" % design, step=step, strategy=strategy, creator=creator)
    types = module.get("num_cells_by_type")
    area, seq = se.num(module.get("area")), se.num(module.get("sequential_area"))
    total = se.num(module.get("num_cells"))
    s_count, s_area = se.num(metrics.get("design__instance__count")), se.num(metrics.get("design__instance__area"))
    extra = {"step": step, "strategy": strategy, "creator": creator, "state_count": s_count, "state_area": s_area}
    if table is None:
        return failed_row("filtered library table unavailable (provenance)", **extra)
    if not isinstance(types, dict) or not types or area is None or seq is None or total is None or s_area is None or s_count is None:
        return failed_row("missing or non-finite metrics", **extra)
    if area <= 0 or s_area <= 0 or not total.is_integer() or total <= 0 or not s_count.is_integer() or s_count <= 0:
        return failed_row("non-positive area or non-integer/non-positive count", **extra)
    types = {t.lstrip("\\"): n for t, n in types.items()}     # module-type names may carry a leading backslash
    if not all(is_pos_int(n) for n in types.values()):
        return failed_row("cell counts are not all positive integers: %s" % types, **extra)
    allowed_bb = BB_MODULES if allow_bb else ()
    unknown = sorted(t for t in types if t not in table and t not in allowed_bb)
    if unknown:
        return failed_row("cells of unknown area (not in the filtered library table): %s" % unknown, **extra)
    bb = {m: types.get(m, 0) for m in allowed_bb}
    if allow_bb and any(n != 1 for n in bb.values()):
        return failed_row("each black box must appear exactly once, found %s" % bb, **extra)
    lib_types = {t: n for t, n in types.items() if t in table}
    lib_cells = sum(lib_types.values())
    if total not in (lib_cells, lib_cells + sum(bb.values())) or (not allow_bb and total != lib_cells):
        return failed_row("num_cells %s is not library cells %s (+ black boxes %s)" % (int(total), lib_cells, sum(bb.values())), **extra)
    weighted = sum(n * table[t] for t, n in lib_types.items())
    if abs(weighted - area) > AREA_TOL or abs(weighted - s_area) > AREA_TOL:
        return failed_row("weighted library area %.4f disagrees with stat %.4f / state %.4f" % (weighted, area, s_area), **extra)
    for line in rpt.splitlines():
        if re.search(r"unknown|without area|no area", line, re.I) and not any(m in line for m in allowed_bb):
            return failed_row("stat.rpt reports an unknown area: %s" % line.strip(), **extra)
    if s_count not in (lib_cells, total):
        return failed_row("state count %s is neither library cells %s nor all cells %s" % (int(s_count), lib_cells, int(total)), **extra)
    return {"status": "valid", "reason": None, "strategy": strategy, "cells_total": int(total), "cells_lib": int(lib_cells),
            "area": area, "sequential_area": seq, "bb_instances": bb if allow_bb else None, "state_count": s_count,
            "state_area": s_area, "cells_by_type": types, "step": step, "creator": creator}


def fmt(v, nd=3):
    return "null" if v is None else ("%.*f" % (nd, v))


def write_reports(out, results, problems, meta):
    status = "FAIL" if problems else "PASS"
    lines = ["# OFFICIAL_BLOCK_PROFILE (official LibreLane %s, synthesis only; diagnosis, NOT a fit proof)" % se.LIBRELANE_VERSION,
             "", "Status: **%s**" % status, "",
             "| probe | status | library cells | area um2 | sequential um2 | excluded black boxes | strategy | Yosys |",
             "|---|---|---:|---:|---:|---|---|---|"]
    for name in PROBES:
        r = results.get(name) or failed_row("not measured")
        bb = ("%s (area EXCLUDED, not zero)" % r["bb_instances"]) if r["bb_instances"] else "-"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, r["status"], "null" if r["cells_lib"] is None else r["cells_lib"], fmt(r["area"]),
            fmt(r["sequential_area"]), bb, r["strategy"], (r["creator"] or "null")[:24]))
    base = meta.get("baseline")
    lines += ["", ("Calibration baseline (current official run `%s`): strategy %s, %s cells, area %s." %
                   (meta["baseline_run"], base["strategy"], base["count"], base["area"])) if base
              else "Calibration baseline unavailable (see problems).", "",
              "The probe areas are NOT additive: each probe optimises across a different boundary, so mul + add + storage "
              "is not the full area and this is not a physical partition. The storage probe excludes the area of the two "
              "black boxes explicitly. add_norm14 is the normaliser module synthesised alone: it is not a share of add "
              "and must not be subtracted from add or summed towards full. 1-tile fit is decided by the main GDS job only."]
    for note in meta.get("notes", []):
        lines.append("Note: " + note)
    if problems:
        lines += ["", "Problems:"] + ["- " + p for p in problems]
    with open(os.path.join(out, "OFFICIAL_BLOCK_PROFILE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "official-block-profile.json"), "w", encoding="utf-8") as f:
        json.dump({"status": status, "problems": problems, "results": results, "meta": meta}, f, indent=2, sort_keys=True)
    with open(os.path.join(out, "STATUS.txt"), "w", encoding="utf-8") as f:
        f.write(status + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="block-profile-out")
    ap.add_argument("--config", default=os.path.join("src", "config_merged.json"))
    ap.add_argument("--runs-root", default=os.path.join("runs", "block-profile"))
    ap.add_argument("--pdk", default=os.environ.get("PDK", "sky130A"))
    ap.add_argument("--baseline-run", default=se.OFFICIAL_RUN_DIR)
    ap.add_argument("--path-map", action="append", default=[], metavar="OLD=NEW",
                    help="explicit prefix mapping of recorded absolute paths (for artifacts downloaded to another host)")
    ap.add_argument("--no-run", action="store_true", help="validate existing probe run directories only")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    problems, results, created = [], {}, []
    path_map = []
    for item in args.path_map:
        if "=" not in item or not item.split("=", 1)[0]:
            problems.append("--path-map %r must be OLD=NEW" % item)
        else:
            path_map.append(tuple(item.split("=", 1)))
    meta = {"config": args.config, "runs_root": args.runs_root, "pdk": args.pdk, "baseline_run": args.baseline_run,
            "baseline": None, "commands": {}, "exit_codes": {}, "no_run": args.no_run, "provenance": {}, "notes": [],
            "path_map": [list(p) for p in path_map]}
    refused = blocked = False
    try:
        runs_abs = os.path.abspath(args.runs_root)
        official_abs = os.path.abspath(se.OFFICIAL_RUN_DIR)
        refused = runs_abs == official_abs or runs_abs.startswith(official_abs + os.sep)
        if refused:
            problems.append("refusing to use the official run directory %s as a probe directory" % se.OFFICIAL_RUN_DIR)
        blocked = refused
        baseline, bp = se.load_baseline(args.baseline_run)
        meta["baseline"] = baseline
        if bp:
            problems.append("baseline: " + bp)
        cfgs = {}
        if not blocked and not args.no_run:
            if baseline is None:
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
            for name in PROBES:
                rd = os.path.join(args.runs_root, name)
                if os.path.exists(rd) and (not os.path.isdir(rd) or os.listdir(rd)):
                    problems.append("run directory %s exists and is not an empty directory" % rd)
                    blocked = True
            try:      # the normaliser probe needs the existing module with its real ports, nothing else
                ports_of(os.path.join(SRC, FILES["add_norm14"][1][0]), FILES["add_norm14"][0], NORM_PORTS)
            except (OSError, RuntimeError) as e:
                problems.append("add_norm14: %s" % e)
                blocked = True
            if not blocked:
                base_cfg = se.read_json(args.config)
                cfg_dir = os.path.dirname(os.path.abspath(args.config))
                with tempfile.NamedTemporaryFile("w", dir=cfg_dir, prefix="phi_probe_bb_", suffix=".v", delete=False,
                                                 encoding="utf-8") as f:
                    f.write(blackbox_text())
                    bb_path = f.name
                created.append(bb_path)
                for name in PROBES:
                    if name == "full":
                        continue
                    cfg = probe_config(base_cfg, name, bb_path)
                    with tempfile.NamedTemporaryFile("w", dir=cfg_dir, prefix="phi_probe_%s_" % name, suffix=".json",
                                                     delete=False, encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2)
                        cfgs[name] = f.name
                    created.append(f.name)
                cfgs["full"] = args.config      # the official configuration, unmodified
                os.makedirs(os.path.join(args.out, "configs"), exist_ok=True)
                for name, path in cfgs.items():
                    shutil.copy(path, os.path.join(args.out, "configs", name + ".json"))
                shutil.copy(bb_path, os.path.join(args.out, "configs", "storage-blackboxes.v"))
                for name in PROBES:
                    rd = os.path.join(args.runs_root, name)
                    os.makedirs(rd, exist_ok=True)   # --force-run-dir needs an existing (here: our own empty) directory
                    # --docker-no-tty BEFORE --dockerized; stop after the synthesis step (no SDC/STA)
                    cmd = [sys.executable, "-m", "librelane", "--docker-no-tty", "--dockerized", "--flow", "Classic",
                           "--to", SYNTH_STEP, "--pdk", args.pdk, "--run-tag", "block-" + name, "--force-run-dir", rd,
                           os.path.relpath(cfgs[name])]
                    meta["commands"][name] = cmd
                    try:
                        rc = se.run_flow(cmd, os.path.join(args.out, name + ".log"))
                    except OSError as e:
                        rc = None
                        problems.append("%s: could not start the flow: %s" % (name, e))
                    meta["exit_codes"][name] = rc
                    if rc != 0:
                        problems.append("%s: tool exit code %s" % (name, rc))
            with open(os.path.join(args.out, "commands.txt"), "w", encoding="utf-8") as f:
                for name, cmd in meta["commands"].items():
                    f.write(" ".join(cmd) + "\n")

        if not refused and (not blocked or args.no_run):
            off_fp, off_table, off_problems = fingerprint(args.baseline_run, path_map)
            meta["provenance"]["official"] = off_fp
            problems += ["official provenance: " + p for p in off_problems]
            for name in PROBES:
                rd = os.path.join(args.runs_root, name)
                fp, table, fp_problems = fingerprint(rd, path_map)
                meta["provenance"][name] = fp
                problems += ["%s provenance: %s" % (name, p) for p in fp_problems]
                results[name] = read_probe(rd, probe_design(name), allow_bb=(name == "storage"), table=table)
                if results[name]["status"] != "valid":
                    problems.append("%s: %s" % (name, results[name]["reason"]))
                if fp is not None and off_fp is not None:
                    diffs = compare_fp(off_fp, fp)
                    problems += ["%s provenance: %s" % (name, x) for x in diffs]
            if baseline is not None:
                for name in PROBES:
                    if results[name]["status"] == "valid" and results[name]["strategy"] != baseline["strategy"]:
                        problems.append("%s: strategy %s differs from the official %s" % (name, results[name]["strategy"], baseline["strategy"]))
                full = results["full"]
                if full["status"] == "valid":
                    if full["cells_total"] != baseline["count"] or abs(full["area"] - baseline["area"]) > 0.001:
                        problems.append("calibration failed: full probe %s cells / %s um2, official run %s cells / %s um2" % (
                            full["cells_total"], fmt(full["area"]), baseline["count"], baseline["area"]))
                    try:
                        base_stat = se.read_json(glob.glob(os.path.join(args.baseline_run, "*-yosys-synthesis", "reports", "stat.json"))[0])
                        base_types = {t.lstrip("\\"): n for t, n in base_stat["modules"]["\\tt_um_trinity_nano"]["num_cells_by_type"].items()}
                        meta["full_cells_by_type_equal_official"] = base_types == full["cells_by_type"]
                        if base_types != full["cells_by_type"]:
                            problems.append("calibration failed: per-type cell counts of the full probe differ from the official run")
                    except (IndexError, OSError, ValueError, KeyError, TypeError, AttributeError) as e:
                        problems.append("official per-type cell counts unreadable: %s" % e)
    except Exception as e:  # report instead of dying silently; the artifact must explain itself
        problems.append("unexpected %s: %s" % (type(e).__name__, e))
    finally:
        for path in created:      # only the files this run created, already copied into the artifact
            try:
                os.remove(path)
            except OSError:
                pass
    for name in PROBES:           # an explicit failed row for anything not measured, never an absent or zero row
        if name not in results:
            results[name] = failed_row("not measured (%s)" % ("refused" if refused else "blocked or tool unavailable; see problems"))
    write_reports(args.out, results, problems, meta)
    print("OFFICIAL_BLOCK_PROFILE %s" % ("FAIL" if problems else "PASS"))
    for p in problems:
        print("  - " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
