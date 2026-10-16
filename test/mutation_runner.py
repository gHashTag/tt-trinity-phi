#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Negative controls: the pin-level test set MUST fail on deliberately broken copies of the RTL.

For the unmodified RTL and for each mutation the runner copies src/ and test/ to a temporary
directory, applies the mutation to the temporary copy only (the repository is never touched
and the production RTL has no mutation hooks), runs the real cocotb pin tests
(`make` in the copy) and reads results.xml.

Verdicts, all fail closed:
  baseline  must run EVERY declared test and pass them all (else the harness is broken)
  KILLED    at least one of the expected tests failed with a PINFAIL message
  SURVIVED  the mutated RTL passed everything            -> harness FAIL
  ERROR     no results.xml, tests missing, mutation text not found exactly once, or a
            failure that is not a PINFAIL (infrastructure problem, not a verdict)  -> FAIL
Exit 0 only if the baseline passes and every mutation is KILLED.
Run inside the cocotb venv, from the repo root:  python3 test/mutation_runner.py
Environment: PHI_RANDOM_N (default 60 here), MUTATION_TIMEOUT (seconds per run, default 900).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_results

TOP = "tt_um_trinity_nano.v"
MUL = "gf16_v2_mul.v"
ADD = "gf16_v2_add.v"
SIGMUL = "gf16_sig_mul10.v"

# (name, file, old text, new text, tests of which at least one must fail with PINFAIL)
MUTATIONS = [
    ("B_forced_to_zero", TOP,
     "wire [15:0] opb = opb_mux;",
     "wire [15:0] opb = 16'h0000;",
     ["test_02_selftest_47c0_8_clocks", "test_03_independent_ab_conformance"]),
    ("write_enables_not_one_hot", TOP,
     "wire       we = wr_accept & dec_hi[HI] & dec_lo[LO];",
     "wire       we = wr_accept & dec_hi[HI];",
     ["test_04_readback_all_cells", "test_05_pointer_wrap_and_go_resets_ptr"]),
    ("readback_group_select_swapped", TOP,
     "(ui_in[2] ? rb1 : rb0)",
     "(ui_in[2] ? rb2 : rb0)",
     ["test_04_readback_all_cells", "test_05_pointer_wrap_and_go_resets_ptr"]),
    ("wrong_uio_oe", TOP,
     "assign uio_oe  = 8'h00;", "assign uio_oe  = 8'hFF;",
     ["test_01_reset_state"]),
    ("signature_shown_as_result", TOP,
     "3'd1:    rd = busy ? 8'h00 : acc[7:0];", "3'd1:    rd = 8'hC0;",
     ["test_01_reset_state"]),
    ("result_visible_while_busy", TOP,
     "3'd2:    rd = busy ? 8'h00 : acc[15:8];", "3'd2:    rd = acc[15:8];",
     ["test_11_result_visibility"]),
    ("err_never_set", TOP,
     "if (wr_rise | go_rise) err <= 1'b1;", "if (1'b0) err <= 1'b1;",
     ["test_10_busy_ignores_and_sets_err"]),
    ("wr_go_priority_swapped", TOP,
     "end else if (wr_rise) begin", "end else if (wr_rise & ~go_rise) begin",
     ["test_09_wr_go_same_clock_idle"]),
    ("ena_ignored", TOP,
     "end else if (ena) begin", "end else begin",
     ["test_08_ena_pause_and_strobe_history"]),
    ("go_does_not_reset_ptr", TOP,
     "end else if (go_rise) begin\n                ptr  <= 4'd0;\n",
     "end else if (go_rise) begin\n",
     ["test_05_pointer_wrap_and_go_resets_ptr"]),
    # The MUL rounding gate exists once per binade (computed in parallel, selected by prod[19]); each
    # gate gets its own mutation and its own conformance vector with an exact tie from the oracle.
    ("wrong_mul_tie_lower_binade", MUL,
     "wire        up_lo   = prod[8] & (|prod[7:0]);",
     "wire        up_lo   = prod[8];",
     ["test_03_independent_ab_conformance"]),
    ("wrong_mul_tie_upper_binade", MUL,
     "wire        up_hi   = prod[9] & (|prod[8:0]);",
     "wire        up_hi   = prod[9];",
     ["test_03_independent_ab_conformance"]),
    ("mul_rounding_carry_dropped", MUL,
     "wire        cy_lo   = (&prod[17:9]) & up_lo;",
     "wire        cy_lo   = 1'b0;",
     ["test_03_independent_ab_conformance"]),
    ("wrong_add_tie", ADD,
     "g & (rest | lsb)", "g & (rest | 1'b1)",
     ["test_03_independent_ab_conformance"]),
    ("add_without_sticky_jam", ADD,
     "{v4[12:1], v4[0] | k4}", "{v4[12:1], v4[0]}",
     ["test_03_independent_ab_conformance"]),
    ("add_stage_sticky_dropped_in_stage_8", ADD,
     "wire        k4 = k3 | (dif[3] & (|v3[7:0]));",
     "wire        k4 = k3;",
     ["test_03_independent_ab_conformance", "test_14_random_vectors"]),
    # Wrong far threshold (>= 8 instead of >= 13). NOT an equivalent mutant: 0x3E01 + 2^-10
    # (exponent difference 10) must round to 0x3E02; far alignment would turn the half-ulp
    # contribution into 1 and give 0x3E01 (vector add_tie_rounds_to_even_up).
    ("add_far_threshold_too_low", ADD,
     "wire        far  = (|dif[5:4]) | (dif[3] & dif[2] & (dif[1] | dif[0]));",
     "wire        far  = (|dif[5:4]) | dif[3];",
     ["test_03_independent_ab_conformance", "test_14_random_vectors"]),
    # The generic full adder of the carry-save multiplier loses the (b & cin) carry term. The pin tests
    # must see a wrong product (this protects the generic branch that all RTL simulation runs; the cell
    # branch is checked separately by test/physical_fa_check.py).
    ("fa_carry_term_dropped", SIGMUL,
     "assign cout = (a & b) | (a & cin) | (b & cin);",
     "assign cout = (a & b) | (a & cin);",
     ["test_03_independent_ab_conformance", "test_14_random_vectors"]),
]


def prepare(tmp, mutation):
    shutil.copytree(os.path.join(ROOT, "src"), os.path.join(tmp, "src"))
    shutil.copytree(HERE, os.path.join(tmp, "test"),
                    ignore=shutil.ignore_patterns("sim_build", "results.xml", "__pycache__",
                                                  "*.vcd", "*.fst"))
    if mutation is None:
        return None
    name, fname, old, new, _ = mutation
    path = os.path.join(tmp, "src", fname)
    with open(path) as f:
        text = f.read()
    if text.count(old) != 1:
        return "mutation %s: text found %d times in %s (must be exactly 1)" % (name, text.count(old), fname)
    with open(path, "w") as f:
        f.write(text.replace(old, new))
    return None


def run_one(mutation):
    tmp = tempfile.mkdtemp(prefix="phi_mut_")
    try:
        problem = prepare(tmp, mutation)
        if problem:
            return "ERROR", problem
        env = dict(os.environ)
        env.setdefault("PHI_RANDOM_N", "60")
        try:
            subprocess.run(["make", "-C", os.path.join(tmp, "test")], env=env,
                           capture_output=True, text=True,
                           timeout=int(os.environ.get("MUTATION_TIMEOUT", "900")))
        except subprocess.TimeoutExpired:
            return "ERROR", "timeout"
        results = os.path.join(tmp, "test", "results.xml")
        if not os.path.isfile(results):
            return "ERROR", "no results.xml (compile or simulator problem)"
        want = check_results.declared_tests(os.path.join(tmp, "test", "test.py"))
        try:
            cases = check_results.load(results)
        except ET.ParseError as e:
            return "ERROR", "results.xml does not parse: %s" % e
        got = sorted(c[0] for c in cases)
        if got != want:
            return "ERROR", "tests missing or unexpected: %s" % sorted(set(want) ^ set(got))
        failed = [(n, txt) for (n, bad, txt) in cases if bad]
        if mutation is None:
            return ("PASS", "") if not failed else ("ERROR", "baseline failed: %s" % [n for n, _ in failed])
        if not failed:
            return "SURVIVED", "all %d tests passed on the mutated RTL" % len(cases)
        notpin = [n for (n, txt) in failed if "PINFAIL" not in txt]
        if notpin:
            return "ERROR", "failure without PINFAIL (not a test verdict) in %s" % notpin
        expected = mutation[4]
        hit = [n for (n, _) in failed if n in expected]
        if not hit:
            return "ERROR", "failed %s but none of the expected %s" % ([n for n, _ in failed], expected)
        return "KILLED", "failed: %s" % [n for n, _ in failed]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    verdict, detail = run_one(None)
    print("baseline (unmodified RTL): %s %s" % (verdict, detail))
    ok = verdict == "PASS"
    if not ok:
        print("MUTATIONS FAIL: the baseline does not pass; mutation results would mean nothing")
        return 1
    killed = 0
    for m in MUTATIONS:
        verdict, detail = run_one(m)
        print("mutation %-28s %-9s %s" % (m[0], verdict, detail))
        if verdict == "KILLED":
            killed += 1
        else:
            ok = False
    print("MUTATIONS %s: %d of %d killed" % ("PASS" if ok else "FAIL", killed, len(MUTATIONS)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
