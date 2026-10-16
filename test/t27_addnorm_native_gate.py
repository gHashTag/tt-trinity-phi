#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native t27c gate for ONE physical measurement sidecar: specs/physical/gf16_dot4_addnorm_probe.t27.

The numeric DOT4 contract keeps its own gate, test/t27_native_gate.py, unchanged (23 tests, its two negative
controls). This adapter has exactly one fixed profile and no option to change it:
  * spec      specs/physical/gf16_dot4_addnorm_probe.t27, module physical-gf16_dot4_addnorm_probe, exactly the
              test blocks addnorm_probe_counts and addnorm_probe_fail_closed (in this order); any other spec,
              including the numeric one, is refused before a tool runs;
  * parse     exit 0 and non-empty output; typecheck `Typecheck OK (0 errors, 0 warnings)`;
  * test-report exit 0, not BLOCKED, tests == 2, pass == 2, FAIL == 0 (an exit 0 without counts fails);
  * seal --save (never --force): `Seal saved to` a file under .trinity/seals that did not exist before; tests
    total == 2, passed == 2, failed == 0, not forced, `vacuous` an integer 0..2 (a count of passes with zero
    RUNTIME asserts, never a bool; compile-time asserts are covered by the negative controls), four real
    gen_hash_* values, test_runner == the pinned witness when --t27-src is given; every seal file that existed
    before is byte-identical afterwards (no foreign seal is overwritten); seal --verify `all hashes MATCH`;
  * two negative controls, each one existing assertion made false (the line must occur exactly once): the copy
    must parse and typecheck and then be DETECTED: exit 1, not BLOCKED, FAIL >= 1; or exit 2 BLOCKED with
    `does not compile` AND `assertion failed` (the Zig @compileError of a false compile-time assertion). A
    missing tool, an import/type/linker error or an all-green run is a failure.
Tool facts (`test-report` output keys, exit codes, seal fields, the relative witness path) are those already
documented and used by test/t27_native_gate.py; only its pure helpers `run` and `counts` are imported, nothing
of its state (errors, summary, thresholds, mutations) is read or written. Each call of main() has its own state.
Never `--force`; T27C_TEST_REPORT_EXIT_ZERO must be unset. Logs, the seal copy, the mutated copies and
`native-summary.json` are written into --out.

Usage (repo root): python3 test/t27_addnorm_native_gate.py --t27c PATH --spec specs/physical/gf16_dot4_addnorm_probe.t27 \
    --out native-addnorm [--t27-src DIR --t27-commit SHA]
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from t27_native_gate import counts, run  # noqa: E402  (pure helpers only)

SPEC = "specs/physical/gf16_dot4_addnorm_probe.t27"
NUMERIC_SPEC = "specs/numeric/gf16_dot4_sky26d.t27"
MODULE = "physical-gf16_dot4_addnorm_probe"
TEST_NAMES = ("addnorm_probe_counts", "addnorm_probe_fail_closed")
EXPECT_TESTS = 2
# (label, exact original line, replacement); each original must occur exactly once in the spec
MUTATIONS = (
    ("false_probe_count_const",
     "    assert(PROBE_COUNT == 5);",
     "    assert(PROBE_COUNT == 6);"),
    ("false_probe_row_valid_call",
     "    assert(probe_row_valid(1, 1, 1, 1, 1, 1) == 1);",
     "    assert(probe_row_valid(1, 1, 1, 1, 1, 1) == 0);"),
)
SEAL_DIR = os.path.join(".trinity", "seals")
WITNESS = "bootstrap/src/test_report.rs"


class Gate:
    def __init__(self):
        self.errors = []
        self.summary = {}

    def fail(self, msg):
        self.errors.append(msg)
        print("ADDNORM_NATIVE_GATE FAIL:", msg)


def spec_problems(spec_arg, text):
    """Why this spec is not the one fixed profile (empty list = it is)."""
    rel = os.path.normpath(spec_arg).replace(os.sep, "/")
    if rel == NUMERIC_SPEC:
        return ["%s is the numeric contract; it belongs to test/t27_native_gate.py, not to this adapter" % rel]
    if rel != SPEC:
        return ["unknown spec %s: this adapter only accepts %s" % (rel, SPEC)]
    if text is None:
        return ["%s is not readable" % rel]
    problems = []
    if not re.search(r"^module\s+%s\s*;" % re.escape(MODULE), text, re.M):
        problems.append("module line 'module %s;' not found" % MODULE)
    names = tuple(re.findall(r'^test\s+"([^"]+)"', text, re.M))
    if names != TEST_NAMES:
        problems.append("test blocks are %s, expected exactly %s" % (list(names), list(TEST_NAMES)))
    for label, old, _ in MUTATIONS:
        if text.count(old) != 1:
            problems.append("negative control %s: line %r found %d times (must be exactly 1)" % (label, old, text.count(old)))
    return problems


def neg_verdict(returncode, stdout):
    """Verdict of test-report on a mutated copy: a string when the false assertion is detected, else None."""
    n = counts(stdout)
    blocked = "BLOCKED" in stdout
    if returncode == 1 and not blocked and (n["FAIL"] or 0) >= 1:
        return "detected by the test runner (FAIL %d)" % n["FAIL"]
    if returncode == 2 and blocked and "does not compile" in stdout and "assertion failed" in stdout \
            and "zig not on PATH" not in stdout:
        return "rejected by the Zig compiler at compile time (BLOCKED: assertion failed)"
    return None


def seal_snapshot():
    snap = {}
    for path in sorted(glob.glob(os.path.join(SEAL_DIR, "*"))):
        if os.path.isfile(path):
            with open(path, "rb") as f:
                snap[os.path.normpath(path)] = hashlib.sha256(f.read()).hexdigest()
    return snap


def place_witness(g, t27_src, commit, created):
    """Same check as test/t27_native_gate.py: the pinned checkout's test_report.rs, byte-equal to the git blob,
    copied to the relative path seal_toolchain() hashes; refused if that path already exists."""
    head = subprocess.run(["git", "-C", t27_src, "rev-parse", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0 or (commit and head.stdout.strip() != commit):
        g.fail("t27 checkout is at %r, expected %r" % (head.stdout.strip(), commit))
        return None
    src = os.path.join(t27_src, WITNESS)
    blob = subprocess.run(["git", "-C", t27_src, "show", "HEAD:" + WITNESS], capture_output=True)
    if blob.returncode != 0 or not os.path.isfile(src):
        g.fail("pinned t27 has no %s" % WITNESS)
        return None
    with open(src, "rb") as f:
        data = f.read()
    if data != blob.stdout:
        g.fail("%s in the checkout differs from the git blob at HEAD" % WITNESS)
        return None
    if os.path.exists(WITNESS):
        g.fail("%s already exists in this repository; refusing to shadow it" % WITNESS)
        return None
    for d in ("bootstrap", "bootstrap/src"):
        if not os.path.isdir(d):
            os.mkdir(d)
            created.append(d)
    with open(WITNESS, "wb") as f:
        f.write(data)
    created.append(WITNESS)
    return hashlib.sha256(data).hexdigest()


def remove_created(created):
    for path in reversed(created):
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            elif os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def check_seal(g, seal, witness_hash):
    tests = seal.get("tests")
    if not isinstance(tests, dict):
        g.fail("seal has no tests record")
        return
    g.summary["seal_tests"] = tests
    if "blocked" in tests:
        g.fail("seal tests record is blocked: %s" % tests.get("blocked"))
    total = tests.get("total")
    if total != EXPECT_TESTS or tests.get("passed") != EXPECT_TESTS or tests.get("failed") != 0:
        g.fail("seal tests record is not exactly %d/%d with 0 failed: %s" % (EXPECT_TESTS, EXPECT_TESTS, tests))
    if tests.get("forced") is True:
        g.fail("seal tests record is forced: %s" % tests)
    vac = tests.get("vacuous")
    if isinstance(vac, bool) or not isinstance(vac, int) or vac < 0 or vac > EXPECT_TESTS:
        g.fail("seal tests.vacuous is %r (type %s): expected an integer 0..%d"
               % (vac, type(vac).__name__, EXPECT_TESTS))
    for k in ("gen_hash_zig", "gen_hash_verilog", "gen_hash_c", "gen_hash_rust"):
        if seal.get(k) in (None, "", "none", "missing"):
            g.fail("seal %s is %r" % (k, seal.get(k)))
    tool = seal.get("toolchain") if isinstance(seal.get("toolchain"), dict) else {}
    g.summary["seal_toolchain"] = tool
    if witness_hash is not None and tool.get("test_runner") != "sha256:" + witness_hash:
        g.fail("seal.toolchain.test_runner is %r, expected sha256:%s" % (tool.get("test_runner"), witness_hash))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--t27c", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--t27-src", default=None)
    ap.add_argument("--t27-commit", default=None)
    args = ap.parse_args(argv)
    g = Gate()
    os.makedirs(args.out, exist_ok=True)

    def finish():
        g.summary["errors"] = list(g.errors)
        with open(os.path.join(args.out, "native-summary.json"), "w") as f:
            json.dump(g.summary, f, indent=2, sort_keys=True)
        if g.errors:
            print("ADDNORM_NATIVE_GATE FAIL: %d problem(s); logs in %s" % (len(g.errors), args.out))
            return 1
        print("ADDNORM_NATIVE_GATE PASS: parse, typecheck, test-report 2/2 0 FAIL, seal --save/--verify, "
              "2 negative controls detected")
        return 0

    try:
        with open(args.spec) as f:
            spec_text = f.read()
    except OSError:
        spec_text = None
    for p in spec_problems(args.spec, spec_text):
        g.fail(p)
    if g.errors:
        return finish()          # refused before any tool runs
    if not os.access(args.t27c, os.X_OK):
        g.fail("t27c is not executable: %s" % args.t27c)
        return finish()
    if os.environ.get("T27C_TEST_REPORT_EXIT_ZERO"):
        g.fail("T27C_TEST_REPORT_EXIT_ZERO is set; it would turn a red test run green")
        return finish()
    zig = shutil.which("zig")
    if not zig:
        g.fail("zig is not on PATH (the test runner needs it; sealing without it is refused)")
        return finish()
    env = dict(os.environ)
    env.pop("T27C_TEST_REPORT_EXIT_ZERO", None)
    g.summary["zig"] = subprocess.run([zig, "version"], capture_output=True, text=True).stdout.strip()
    with open(os.path.join(args.out, "toolchain.txt"), "w") as f:
        f.write("zig %s at %s\nt27c %s\nspec %s\n" % (g.summary["zig"], zig, args.t27c, SPEC))

    # 1. parse, typecheck
    p = run("parse", [args.t27c, "parse", args.spec], args.out, env)
    if p.returncode != 0 or not p.stdout.strip():
        g.fail("parse exit %d or empty output" % p.returncode)
    p = run("typecheck", [args.t27c, "typecheck", args.spec], args.out, env)
    if p.returncode != 0 or not re.search(r"Typecheck OK \(0 errors, 0 warnings\)", p.stdout + p.stderr):
        g.fail("typecheck exit %d or not '0 errors, 0 warnings'" % p.returncode)

    # 2. test-report: exact counts of this sidecar
    p = run("test-report", [args.t27c, "test-report", args.spec, "--specs-dir", "specs", "--verbose"], args.out, env)
    nums = counts(p.stdout)
    g.summary["test_report"] = nums
    if p.returncode != 0:
        g.fail("test-report exit %d (1 = a test FAILS, 2 = BLOCKED)" % p.returncode)
    if "BLOCKED" in p.stdout:
        g.fail("test-report is BLOCKED: blocked is not a pass")
    if nums["tests"] != EXPECT_TESTS or nums["pass"] != EXPECT_TESTS or nums["FAIL"] != 0:
        g.fail("test-report tests=%s pass=%s FAIL=%s, expected exactly %d/%d/0 (missing counts are not a pass)"
               % (nums["tests"], nums["pass"], nums["FAIL"], EXPECT_TESTS, EXPECT_TESTS))
    m = re.search(r"vacuous passes\s+(\d+) of (\d+)", p.stdout)
    g.summary["runtime_assert_vacuous_line"] = m.group(0) if m else None

    # 3. seal --save / --verify with the pinned witness; no foreign seal may change
    created, witness_hash = [], None
    try:
        if args.t27_src:
            witness_hash = place_witness(g, args.t27_src, args.t27_commit, created)
            g.summary["test_runner_witness_sha256"] = witness_hash
        before = seal_snapshot()
        p = run("seal-save", [args.t27c, "seal", args.spec, "--save"], args.out, env)
        m = re.search(r"Seal saved to (\S+)", p.stdout)
        seal_path = None
        if p.returncode != 0 or not m:
            g.fail("seal --save exit %d or no 'Seal saved to' line (never --force)" % p.returncode)
        else:
            seal_path = os.path.normpath(m.group(1))
            g.summary["seal_path"] = seal_path
            if os.path.normpath(os.path.dirname(seal_path)) != os.path.normpath(SEAL_DIR):
                g.fail("seal %s is not under %s" % (seal_path, SEAL_DIR))
            if seal_path in before:
                g.fail("seal %s existed before this run; refusing to overwrite a seal" % seal_path)
            if not os.path.isfile(seal_path):
                g.fail("seal file %s does not exist" % seal_path)
                seal_path = None
        if seal_path:
            shutil.copy(seal_path, os.path.join(args.out, os.path.basename(seal_path)))
            try:
                with open(seal_path) as f:
                    seal = json.load(f)
            except ValueError as e:
                seal = {}
                g.fail("seal %s is not JSON: %s" % (seal_path, e))
            check_seal(g, seal if isinstance(seal, dict) else {}, witness_hash)
        p = run("seal-verify", [args.t27c, "seal", args.spec, "--verify"], args.out, env)
        if p.returncode != 0 or "all hashes MATCH" not in p.stdout:
            g.fail("seal --verify exit %d or not 'all hashes MATCH'" % p.returncode)
        after = seal_snapshot()
        changed = sorted(k for k, h in before.items() if after.get(k) != h)
        if changed:
            g.fail("seal files that existed before were changed or removed: %s" % changed)
    finally:
        remove_created(created)

    # 4. negative controls (never sealed)
    negdir = os.path.join(args.out, "negctl")
    os.makedirs(negdir, exist_ok=True)
    g.summary["negative_control"] = {}
    for label, old, new in MUTATIONS:
        mpath = os.path.join(negdir, label + ".t27")
        with open(mpath, "w") as f:
            f.write(spec_text.replace(old, new))
        pp = run("neg-%s-parse" % label, [args.t27c, "parse", mpath], args.out, env)
        pt = run("neg-%s-typecheck" % label, [args.t27c, "typecheck", mpath], args.out, env)
        if pp.returncode != 0 or pt.returncode != 0:
            g.fail("negative control %s: the mutated spec must still parse and typecheck (parse %d, typecheck %d)"
                   % (label, pp.returncode, pt.returncode))
        pr = run("neg-%s-test-report" % label, [args.t27c, "test-report", mpath, "--specs-dir", "specs"], args.out, env)
        verdict = neg_verdict(pr.returncode, pr.stdout)
        if verdict is None:
            g.fail("negative control %s NOT detected: test-report exit %d, counts %s"
                   % (label, pr.returncode, counts(pr.stdout)))
        g.summary["negative_control"][label] = {"exit": pr.returncode, "counts": counts(pr.stdout),
                                                "blocked": "BLOCKED" in pr.stdout, "verdict": verdict}
        print("negative control %-28s -> %s" % (label, verdict))
    return finish()


if __name__ == "__main__":
    sys.exit(main())
