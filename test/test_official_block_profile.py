#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fixture tests of test/official_block_profile.py (policy: specs/physical/gf16_dot4_addnorm_probe.t27).

No LibreLane, Docker or PDK is needed: every check uses `--no-run` on small hand-written run directories (a
four-cell fake Liberty file with round areas, so every expected area below is written out by hand, not
recomputed with the profiler's own code). The docker image id is replaced by a fixed string; everything else
goes through the real script. Covered: the new add_norm14 row is valid and reported; a missing probe, an
unknown cell, a filtered library with different bytes, a wrong DESIGN_NAME and a failed full calibration all
FAIL; the report never drops a row; the temporary config of add_norm14 points at the right module and file and
changes nothing else; the real src/gf16_v2_add.v still contains gf16_add_norm14 with its ports.

Usage (repo root): python3 test/test_official_block_profile.py      (exit 0 = all tests pass)
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import official_block_profile as obp  # noqa: E402

PDK_ROOT = "/fixture/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71"
AND2, MUX2, DFF, XOR2 = "sky130_fd_sc_hd__and2_2", "sky130_fd_sc_hd__mux2_1", "sky130_fd_sc_hd__dfrtp_2", "sky130_fd_sc_hd__xor2_2"
LIB_TEXT = """library ("fixture") {
    cell ("sky130_fd_sc_hd__and2_2") {
        area : 7.5;
    }
    cell ("sky130_fd_sc_hd__mux2_1") {
        area : 11.25;
    }
    cell ("sky130_fd_sc_hd__dfrtp_2") {
        area : 26.25;
    }
    cell ("sky130_fd_sc_hd__inv_2") {
        area : 3.75;
    }
}
"""
# hand-computed fixture rows: (DESIGN_NAME, cells by type, area, sequential area, num_cells, state count)
#   full/baseline: 2 dfrtp (52.5) + 3 mux2 (33.75)          = 86.25
#   mul:           2 and2                                    = 15.0
#   add:           1 mux2 + 1 and2                           = 18.75
#   add_norm14:    4 mux2 (45.0) + 2 and2 (15.0)             = 60.0
#   storage:       2 dfrtp + 1 mux2 = 63.75, plus the two black boxes (area excluded)
ROWS = {
    "full": ("tt_um_trinity_nano", {DFF: 2, MUX2: 3}, 86.25, 52.5, 5, 5),
    "mul": ("gf16_v2_mul", {AND2: 2}, 15.0, 0.0, 2, 2),
    "add": ("gf16_v2_add", {MUX2: 1, AND2: 1}, 18.75, 0.0, 2, 2),
    "add_norm14": ("gf16_add_norm14", {MUX2: 4, AND2: 2}, 60.0, 0.0, 6, 6),
    "storage": ("tt_um_trinity_nano", {DFF: 2, MUX2: 1, "gf16_v2_mul": 1, "gf16_v2_add": 1}, 63.75, 52.5, 5, 3),
}
ALL_PROBES = ("full", "mul", "add", "add_norm14", "storage")


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


class Fixture:
    def __init__(self, root):
        self.root = root
        self.lib = os.path.join(root, "pdk", "filtered.lib")
        self.orig = os.path.join(root, "pdk", "original.lib")
        self.excl = [os.path.join(root, "pdk", "no_synth.cells"), os.path.join(root, "pdk", "drc_exclude.cells")]
        os.makedirs(os.path.join(root, "pdk"))
        for p, text in ((self.lib, LIB_TEXT), (self.orig, LIB_TEXT + "/* original */\n"),
                        (self.excl[0], "sky130_fd_sc_hd__a21oi_1\n"), (self.excl[1], "sky130_fd_sc_hd__and2_0\n")):
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        self.base = os.path.join(root, "wokwi")
        self.runs = os.path.join(root, "runs")
        self.out = os.path.join(root, "out")
        self.make_run(self.base, "full")
        for name in ALL_PROBES:
            self.make_run(os.path.join(self.runs, name), name)

    def make_run(self, run_dir, name, design=None, types=None, lib=None, baseline_area=None):
        d_name, d_types, area, seq, cells, s_count = ROWS[name]
        design = design or d_name
        types = d_types if types is None else types
        d = os.path.join(run_dir, "06-yosys-synthesis")
        if os.path.isdir(run_dir):
            shutil.rmtree(run_dir)
        os.makedirs(os.path.join(d, "reports"))
        write_json(os.path.join(d, "config.json"), {
            "meta": {"step": "Yosys.Synthesis", "librelane_version": "3.0.14"}, "DESIGN_NAME": design,
            "SYNTH_STRATEGY": "AREA 0", "PDK": "sky130A", "PDK_ROOT": PDK_ROOT, "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
            "EXTRA_EXCLUDED_CELLS": None, "SYNTH_EXCLUDED_CELL_FILE": self.excl[0], "PNR_EXCLUDED_CELL_FILE": self.excl[1]})
        write_json(os.path.join(d, "extra.json"), {"libs_synth": [lib or self.lib], "blackbox_models": [self.orig]})
        write_json(os.path.join(d, "state_out.json"), {"metrics": {
            "design__instance__count": s_count, "design__instance__area": baseline_area if baseline_area is not None else area}})
        write_json(os.path.join(d, "reports", "stat.json"), {"creator": "Yosys 0.62 (fixture)", "modules": {
            "\\" + design: {"num_cells_by_type": types, "area": area, "sequential_area": seq, "num_cells": cells}}})
        rpt = "Chip area for module '\\%s': %.6f\n" % (design, area)
        if name == "storage":
            rpt += "   Area for cell type \\gf16_v2_mul is unknown!\n   Area for cell type \\gf16_v2_add is unknown!\n"
        with open(os.path.join(d, "reports", "stat.rpt"), "w", encoding="utf-8") as f:
            f.write(rpt)

    def run(self):
        argv = ["official_block_profile.py", "--no-run", "--runs-root", self.runs, "--baseline-run", self.base, "--out", self.out]
        old_argv, old_img = sys.argv, obp.docker_image_id
        sys.argv, obp.docker_image_id = argv, (lambda: "sha256:fixture-image")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = obp.main()
        finally:
            sys.argv, obp.docker_image_id = old_argv, old_img
        with open(os.path.join(self.out, "official-block-profile.json"), encoding="utf-8") as f:
            report = json.load(f)
        with open(os.path.join(self.out, "OFFICIAL_BLOCK_PROFILE.md"), encoding="utf-8") as f:
            md = f.read()
        return rc, report, md


class OfficialBlockProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="obp_fixture_")
        self.fx = Fixture(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_probe_set_is_exactly_the_five(self):
        self.assertEqual(tuple(obp.PROBES), ALL_PROBES)

    def test_valid_profile_reports_the_norm_row(self):
        rc, report, md = self.fx.run()
        self.assertEqual(rc, 0, report["problems"])
        self.assertEqual(report["status"], "PASS")
        row = report["results"]["add_norm14"]
        self.assertEqual(row["status"], "valid")
        self.assertEqual(row["cells_lib"], 6)
        self.assertAlmostEqual(row["area"], 60.0, places=6)
        self.assertIn("| add_norm14 | valid | 6 | 60.000 |", md)
        self.assertIn("must not be subtracted from add", md)
        for name in ALL_PROBES:
            self.assertEqual(report["results"][name]["status"], "valid", name)

    def test_missing_norm_probe_fails(self):
        shutil.rmtree(os.path.join(self.fx.runs, "add_norm14"))
        rc, report, md = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["results"]["add_norm14"]["status"], "failed")
        self.assertIsNone(report["results"]["add_norm14"]["area"])
        self.assertIn("| add_norm14 | failed | null | null |", md)

    def test_unknown_cell_fails_and_is_not_zero(self):
        self.fx.make_run(os.path.join(self.fx.runs, "add_norm14"), "add_norm14", types={MUX2: 4, AND2: 2, XOR2: 1})
        rc, report, _ = self.fx.run()
        self.assertEqual(rc, 1)
        row = report["results"]["add_norm14"]
        self.assertEqual(row["status"], "failed")
        self.assertIsNone(row["area"])
        self.assertIn(XOR2, row["reason"])

    def test_filtered_library_with_other_bytes_fails(self):
        other = os.path.join(self.tmp, "pdk", "filtered-other.lib")
        with open(other, "w", encoding="utf-8") as f:
            f.write(LIB_TEXT + "/* same cells and areas, different bytes */\n")
        self.fx.make_run(os.path.join(self.fx.runs, "add_norm14"), "add_norm14", lib=other)
        rc, report, _ = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertTrue(any(p.startswith("add_norm14 provenance:") and "raw sha256" in p for p in report["problems"]),
                        report["problems"])

    def test_wrong_design_name_fails(self):
        self.fx.make_run(os.path.join(self.fx.runs, "add_norm14"), "add_norm14", design="gf16_v2_add")
        rc, report, _ = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertEqual(report["results"]["add_norm14"]["status"], "failed")
        self.assertIn("gf16_add_norm14", report["results"]["add_norm14"]["reason"])

    def test_failed_calibration_fails_the_run(self):
        self.fx.make_run(self.fx.base, "full", baseline_area=87.5)    # official run differs from the fresh full probe
        rc, report, _ = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("calibration failed" in p for p in report["problems"]), report["problems"])

    def test_report_never_drops_a_row(self):
        out = os.path.join(self.tmp, "report-only")
        os.makedirs(out)
        obp.write_reports(out, {}, ["fixture problem"], {"baseline": None, "baseline_run": "fixture"})
        with open(os.path.join(out, "OFFICIAL_BLOCK_PROFILE.md"), encoding="utf-8") as f:
            md = f.read()
        for name in ALL_PROBES:
            self.assertIn("| %s | failed | null | null |" % name, md)
        with open(os.path.join(out, "STATUS.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "FAIL")

    def test_norm_config_changes_only_design_and_files(self):
        base = {"DESIGN_NAME": "tt_um_trinity_nano", "VERILOG_FILES": ["dir::tt_um_trinity_nano.v"],
                "SYNTH_STRATEGY": "AREA 0", "CLOCK_PERIOD": 20, "PL_TARGET_DENSITY_PCT": 45,
                "EXTRA_EXCLUDED_CELLS": None, "SYNTH_DEFINES": ["__pnr__"]}
        snapshot = json.dumps(base, sort_keys=True)
        cfg = obp.probe_config(base, "add_norm14")
        self.assertEqual(cfg["DESIGN_NAME"], "gf16_add_norm14")
        # the normaliser module comes from the unchanged adder file; gf16_sig_mul10.v only defines gf16_fa1
        self.assertEqual(cfg["VERILOG_FILES"], ["dir::gf16_v2_add.v", "dir::gf16_sig_mul10.v"])
        for key in ("SYNTH_STRATEGY", "CLOCK_PERIOD", "PL_TARGET_DENSITY_PCT", "EXTRA_EXCLUDED_CELLS", "SYNTH_DEFINES"):
            self.assertEqual(cfg[key], base[key], key)
        self.assertEqual(set(cfg), set(base))
        self.assertEqual(json.dumps(base, sort_keys=True), snapshot)      # the official config is not mutated
        self.assertEqual(obp.probe_config(base, "add")["DESIGN_NAME"], "gf16_v2_add")
        with self.assertRaises(ValueError):
            obp.probe_config(base, "full")

    def test_real_source_has_the_normaliser_ports(self):
        path = os.path.join(os.path.dirname(HERE), "src", "gf16_v2_add.v")
        obp.ports_of(path, "gf16_add_norm14", {("input", 13, 0, "x"), ("output", 13, 0, "norm"), ("output", 3, 0, "lz")})
        with self.assertRaises(RuntimeError):
            obp.ports_of(path, "gf16_add_norm14", {("input", 15, 0, "x"), ("output", 13, 0, "norm"), ("output", 3, 0, "lz")})
        with self.assertRaises(RuntimeError):
            obp.ports_of(path, "gf16_add_norm15", {("input", 13, 0, "x")})


if __name__ == "__main__":
    unittest.main()
