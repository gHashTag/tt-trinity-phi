#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fixture tests of test/t27_addnorm_native_gate.py (no real t27c, Zig or Docker).

A small fake `t27c` and a fake `zig` are written into a temporary folder; the fake t27c answers each subcommand
with output in the documented format (see test/t27_native_gate.py), driven by a scenario name in the
environment, and records every call. The real sidecar specs/physical/gf16_dot4_addnorm_probe.t27 is copied into
a temporary repository root. These tests check the adapter's DECISIONS on given tool outputs: the exact 2/2/0
profile, the two false mutations, the refusal of the numeric and of an unknown spec, seal checks and the
protection of foreign seal files, and that importing and running the adapter leaves the numeric gate's
thresholds, mutations and state untouched. Whether the real native toolchain accepts the sidecar is only
known from the CI job t27-native.

Usage (repo root): python3 test/test_t27_addnorm_native_gate.py      (exit 0 = all tests pass)
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
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import t27_native_gate as numeric_gate  # noqa: E402
import t27_addnorm_native_gate as gate  # noqa: E402

REAL_SIDECAR = os.path.join(ROOT, "specs", "physical", "gf16_dot4_addnorm_probe.t27")
SIDECAR_REL = "specs/physical/gf16_dot4_addnorm_probe.t27"

FAKE_T27C = r'''#!/usr/bin/env python3
import json, os, sys
scenario = os.environ.get("FAKE_SCENARIO", "ok")
with open(os.environ["FAKE_CALLS"], "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
cmd, spec = sys.argv[1], sys.argv[2]
neg = "negctl" in spec
if cmd == "parse":
    print("parsed module ok"); sys.exit(0)
if cmd == "typecheck":
    print("Typecheck OK (0 errors, 0 warnings)"); sys.exit(0)
if cmd == "test-report":
    if neg:
        if scenario == "neg_undetected":
            print("tests 2\npass 2\nFAIL 0"); sys.exit(0)
        if scenario == "neg_blocked_import":
            print("BLOCKED: generated Zig does not compile: error: unable to find import"); sys.exit(2)
        if scenario == "neg_blocked_assert":
            print("BLOCKED: generated Zig does not compile: error: assertion failed"); sys.exit(2)
        print("tests 2\npass 1\nFAIL 1"); sys.exit(1)
    if scenario == "count23":
        print("tests 23\npass 23\nFAIL 0"); sys.exit(0)
    if scenario == "nocounts":
        print("all good"); sys.exit(0)
    print("tests 2\npass 2\nFAIL 0\nvacuous passes 2 of 2"); sys.exit(0)
if cmd == "seal":
    path = os.path.join(".trinity", "seals", "physical-gf16_dot4_addnorm_probe.json")
    if sys.argv[3] == "--save":
        os.makedirs(os.path.dirname(path), exist_ok=True)
        vac = True if scenario == "vac_bool" else 2
        seal = {"tests": {"total": 2, "passed": 2, "failed": 0, "failing": [], "forced": False, "vacuous": vac},
                "gen_hash_zig": "sha256:z", "gen_hash_verilog": "sha256:v", "gen_hash_c": "sha256:c",
                "gen_hash_rust": "sha256:r", "toolchain": {"zig": "0.16.0", "test_runner": "missing"}}
        with open(path, "w") as f:
            json.dump(seal, f)
        if scenario == "clobber":
            with open(os.path.join(".trinity", "seals", "triformat-gf16_dot4.json"), "w") as f:
                f.write("{}")
        print("Seal saved to " + path); sys.exit(0)
    print("all hashes MATCH"); sys.exit(0)
sys.exit(3)
'''
FAKE_ZIG = "#!/bin/sh\necho 0.16.0\n"


class AddnormNativeGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="addnorm_gate_")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(self.repo, "specs", "physical"))
        os.makedirs(os.path.join(self.repo, ".trinity", "seals"))
        shutil.copy(REAL_SIDECAR, os.path.join(self.repo, SIDECAR_REL))
        with open(os.path.join(self.repo, ".trinity", "seals", "triformat-gf16_dot4.json"), "w") as f:
            f.write('{"numeric": "seal of the other gate"}')
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir)
        self.t27c = os.path.join(bindir, "t27c")
        for path, text in ((self.t27c, FAKE_T27C), (os.path.join(bindir, "zig"), FAKE_ZIG)):
            with open(path, "w") as f:
                f.write(text)
            os.chmod(path, 0o755)
        self.calls = os.path.join(self.tmp, "calls.txt")
        open(self.calls, "w").close()
        self.old_env, self.old_cwd = dict(os.environ), os.getcwd()
        os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")
        os.environ["FAKE_CALLS"] = self.calls
        os.environ.pop("T27C_TEST_REPORT_EXIT_ZERO", None)
        os.chdir(self.repo)

    def tearDown(self):
        os.chdir(self.old_cwd)
        os.environ.clear()
        os.environ.update(self.old_env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def gate_run(self, scenario="ok", spec=SIDECAR_REL, fresh=True):
        own_seal = os.path.join(".trinity", "seals", "physical-gf16_dot4_addnorm_probe.json")
        if fresh and os.path.exists(own_seal):
            os.remove(own_seal)          # a fresh CI checkout has no seal of the sidecar
        open(self.calls, "w").close()
        os.environ["FAKE_SCENARIO"] = scenario
        out = os.path.join(self.tmp, "out-" + scenario)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = gate.main(["--t27c", self.t27c, "--spec", spec, "--out", out])
        with open(os.path.join(out, "native-summary.json")) as f:
            summary = json.load(f)
        with open(self.calls) as f:
            calls = f.read().splitlines()
        return rc, summary, calls

    def test_valid_run_passes_with_exact_counts(self):
        rc, summary, calls = self.gate_run("ok")
        self.assertEqual(rc, 0, summary["errors"])
        self.assertEqual(summary["test_report"], {"tests": 2, "pass": 2, "FAIL": 0})
        self.assertEqual(sorted(summary["negative_control"]), ["false_probe_count_const", "false_probe_row_valid_call"])
        self.assertTrue(all(v["verdict"] for v in summary["negative_control"].values()))
        self.assertIn("seal %s --save" % SIDECAR_REL, calls)
        self.assertFalse(any("--force" in c for c in calls))

    def test_mutated_copies_are_false_versions_of_the_real_lines(self):
        self.gate_run("ok")
        negdir = os.path.join(self.tmp, "out-ok", "negctl")
        with open(os.path.join(negdir, "false_probe_count_const.t27")) as f:
            a = f.read()
        with open(os.path.join(negdir, "false_probe_row_valid_call.t27")) as f:
            b = f.read()
        self.assertIn("    assert(PROBE_COUNT == 6);", a)
        self.assertNotIn("    assert(PROBE_COUNT == 5);", a)
        self.assertIn("    assert(probe_row_valid(1, 1, 1, 1, 1, 1) == 0);", b)
        self.assertNotIn("    assert(probe_row_valid(1, 1, 1, 1, 1, 1) == 1);", b)

    def test_numeric_counts_are_rejected(self):
        rc, summary, _ = self.gate_run("count23")
        self.assertEqual(rc, 1)
        self.assertTrue(any("expected exactly 2/2/0" in e for e in summary["errors"]))

    def test_exit_zero_without_counts_fails(self):
        rc, summary, _ = self.gate_run("nocounts")
        self.assertEqual(rc, 1)

    def test_undetected_mutation_fails(self):
        rc, summary, _ = self.gate_run("neg_undetected")
        self.assertEqual(rc, 1)
        self.assertTrue(all(v["verdict"] is None for v in summary["negative_control"].values()))

    def test_blocked_by_import_error_is_not_detection(self):
        rc, summary, _ = self.gate_run("neg_blocked_import")
        self.assertEqual(rc, 1)

    def test_blocked_by_assertion_failed_is_detection(self):
        rc, summary, _ = self.gate_run("neg_blocked_assert")
        self.assertEqual(rc, 0, summary["errors"])

    def test_boolean_vacuous_fails(self):
        rc, summary, _ = self.gate_run("vac_bool")
        self.assertEqual(rc, 1)
        self.assertTrue(any("vacuous" in e for e in summary["errors"]))

    def test_foreign_seal_change_fails(self):
        rc, summary, _ = self.gate_run("clobber")
        self.assertEqual(rc, 1)
        self.assertTrue(any("triformat-gf16_dot4.json" in e for e in summary["errors"]))

    def test_existing_sidecar_seal_is_not_overwritten(self):
        self.gate_run("ok")
        rc, summary, _ = self.gate_run("ok", fresh=False)
        self.assertEqual(rc, 1)
        self.assertTrue(any("refusing to overwrite" in e for e in summary["errors"]))

    def test_numeric_spec_is_refused_before_any_tool(self):
        os.makedirs(os.path.join(self.repo, "specs", "numeric"))
        with open(os.path.join(self.repo, "specs", "numeric", "gf16_dot4_sky26d.t27"), "w") as f:
            f.write("module triformat-gf16_dot4;\n")
        rc, summary, calls = self.gate_run("ok", spec="specs/numeric/gf16_dot4_sky26d.t27")
        self.assertEqual(rc, 1)
        self.assertEqual(calls, [])
        self.assertTrue(any("numeric contract" in e for e in summary["errors"]))

    def test_unknown_or_altered_physical_spec_is_refused(self):
        with open(SIDECAR_REL) as f:
            text = f.read()
        with open(SIDECAR_REL, "w") as f:
            f.write(text.replace('test "addnorm_probe_fail_closed"', 'test "addnorm_probe_other"'))
        rc, summary, calls = self.gate_run("ok")
        self.assertEqual(rc, 1)
        self.assertEqual(calls, [])
        other = "specs/physical/other.t27"
        shutil.copy(REAL_SIDECAR, other)
        rc, summary, calls = self.gate_run("ok", spec=other)
        self.assertEqual(rc, 1)
        self.assertEqual(calls, [])

    def test_real_sidecar_matches_the_profile(self):
        with open(REAL_SIDECAR) as f:
            self.assertEqual(gate.spec_problems(SIDECAR_REL, f.read()), [])

    def test_numeric_gate_state_is_untouched(self):
        self.gate_run("ok")
        self.gate_run("neg_undetected")
        self.assertEqual(numeric_gate.EXPECT_MIN_TESTS, 23)
        self.assertEqual(numeric_gate.MUTATIONS, [
            ("false_const_assert", "    assert(UIO_OE_ALL == 0);", "    assert(UIO_OE_ALL == 1);"),
            ("false_call_assert", "    assert(dot4_rise(1, 0) == 1);", "    assert(dot4_rise(1, 0) == 0);")])
        self.assertEqual(numeric_gate.errors, [])
        self.assertEqual(numeric_gate.summary, {})

    def test_each_run_has_its_own_state(self):
        rc1, _, _ = self.gate_run("neg_undetected")
        rc2, summary, _ = self.gate_run("ok")
        self.assertEqual((rc1, rc2), (1, 0))
        self.assertEqual(summary["errors"], [])


if __name__ == "__main__":
    unittest.main()
