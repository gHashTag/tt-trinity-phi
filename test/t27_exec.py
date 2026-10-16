#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Executes every `test` and `invariant` block of specs/numeric/gf16_dot4_sky26d.t27.

t27c parse / typecheck check syntax and types only; they do not evaluate `assert`. This
narrow adapter transpiles the small, fixed subset of .t27 that the spec uses (u16 constants,
pure functions made of `if (...) { return ...; }` and `return ...;`, `test "..." { assert(...); }`
and `invariant name / assert ...`) to Python and evaluates every assertion.

It FAILS CLOSED: an unknown construct, an unknown block name, a block with no assertion, a
different number of tests or invariants, or any false assertion is an error. This is not
t27c and it is not the t27 seal; it is an honest equivalent for executing the assertions.

Usage: python3 test/t27_exec.py [path/to/spec.t27]      (exit 0 = all assertions hold)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SPEC = os.path.join(HERE, "..", "specs", "numeric", "gf16_dot4_sky26d.t27")

EXPECTED_TESTS = [
    "dot4_uio_is_input_only", "dot4_reserved_bits_are_uio_7_5", "dot4_pin_fields",
    "dot4_readback_address_uses_low_nibble", "dot4_rising_edge", "dot4_pointer_wraps_at_16",
    "dot4_memory_map", "dot4_status_byte", "dot4_read_map", "dot4_signature_is_reset_anchor",
    "dot4_selftest_operand_fields", "dot4_selftest_result_is_30", "dot4_zero_classes",
    "dot4_no_subnormals_smallest_code", "dot4_special_classes", "dot4_canon_zero",
    "dot4_mul_round_tie_goes_toward_zero", "dot4_add_round_tie_goes_to_even",
    "dot4_underflow_and_gap_flush", "dot4_overflow_threshold", "dot4_mul_invalid_cases",
    "dot4_add_invalid_cases", "dot4_latency_is_eight_clocks",
]
EXPECTED_INVARIANTS = [
    "dot4_uio_input_only", "dot4_signature_matches_selftest", "dot4_read_map_total",
    "dot4_pointer_period_16", "dot4_mul_tie_is_not_rounded_up",
]


class SpecError(Exception):
    pass


def clean_lines(text):
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("//") or s.startswith(";"):
            out.append("")
            continue
        i = ln.find("//")
        if i >= 0:
            ln = ln[:i]
        out.append(ln.rstrip())
    return out


def conv(expr):
    e = re.sub(r"!(?!=)", " not ", expr)
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    return e


def parse_consts(lines, env):
    pat = re.compile(r"^pub const (\w+)\s*:\s*\w+\s*=\s*(.+);$")
    for ln in lines:
        m = pat.match(ln)
        if m:
            env[m.group(1)] = eval(conv(m.group(2)), {}, env)


def parse_functions(lines, env):
    head = re.compile(r"^pub fn (\w+)\((.*)\)\s*(\w+)\s*\{$")
    names = []
    i = 0
    while i < len(lines):
        m = head.match(lines[i])
        if not m:
            i += 1
            continue
        name = m.group(1)
        params = [p.split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]
        py = ["def %s(%s):" % (name, ", ".join(params))]
        depth = 1
        indent = 1
        i += 1
        while depth > 0:
            if i >= len(lines):
                raise SpecError("function %s is not closed" % name)
            s = lines[i].strip()
            i += 1
            if not s:
                continue
            mi = re.match(r"^if \((.*)\) \{$", s)
            mr = re.match(r"^return (.*);$", s)
            if mi:
                py.append("    " * indent + "if %s:" % conv(mi.group(1)))
                indent += 1
                depth += 1
            elif s == "}":
                depth -= 1
                indent -= 1
            elif mr:
                py.append("    " * indent + "return %s" % conv(mr.group(1)))
            else:
                raise SpecError("unsupported statement in %s: %r" % (name, s))
        exec("\n".join(py), env)
        names.append(name)
    return names


def run_blocks(lines, env):
    tests, invs = {}, {}
    test_head = re.compile(r'^test "([^"]+)" \{$')
    inv_head = re.compile(r"^invariant (\w+)$")
    n = 0
    i = 0
    while i < len(lines):
        mt = test_head.match(lines[i])
        mi = inv_head.match(lines[i])
        if mt:
            name = mt.group(1)
            i += 1
            count = 0
            while lines[i].strip() != "}":
                s = lines[i].strip()
                i += 1
                if not s:
                    continue
                ma = re.match(r"^assert\((.*)\);$", s)
                if not ma:
                    raise SpecError("test %s: unsupported statement %r" % (name, s))
                if not eval(conv(ma.group(1)), env):
                    raise SpecError("test %s: assertion FALSE: %s" % (name, ma.group(1)))
                count += 1
            if count == 0:
                raise SpecError("test %s has no assertion" % name)
            if name in tests:
                raise SpecError("duplicate test %s" % name)
            tests[name] = count
            n += count
        elif mi:
            name = mi.group(1)
            i += 1
            count = 0
            while i < len(lines):
                s = lines[i]
                if not s.strip():
                    if count:
                        break
                    i += 1
                    continue
                if not s.startswith((" ", "\t")):
                    break
                ma = re.match(r"^\s+assert (.*)$", s)
                if not ma:
                    raise SpecError("invariant %s: unsupported statement %r" % (name, s))
                if not eval(conv(ma.group(1)), env):
                    raise SpecError("invariant %s: assertion FALSE: %s" % (name, ma.group(1)))
                count += 1
                i += 1
            if count == 0:
                raise SpecError("invariant %s has no assertion" % name)
            if name in invs:
                raise SpecError("duplicate invariant %s" % name)
            invs[name] = count
            n += count
        else:
            i += 1
    return tests, invs, n


def load_spec(path=DEFAULT_SPEC):
    """Parse constants and functions; returns the evaluation environment."""
    with open(path) as f:
        lines = clean_lines(f.read())
    env = {}
    parse_consts(lines, env)
    parse_functions(lines, env)
    return env, lines


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT_SPEC
    try:
        env, lines = load_spec(path)
        tests, invs, n = run_blocks(lines, env)
    except (SpecError, NameError, SyntaxError, TypeError, IndexError) as e:
        print("T27_EXEC FAIL: %s: %s" % (type(e).__name__, e))
        return 1
    if sorted(tests) != sorted(EXPECTED_TESTS):
        print("T27_EXEC FAIL: test names differ. missing=%s unknown=%s" % (
            sorted(set(EXPECTED_TESTS) - set(tests)), sorted(set(tests) - set(EXPECTED_TESTS))))
        return 1
    if sorted(invs) != sorted(EXPECTED_INVARIANTS):
        print("T27_EXEC FAIL: invariant names differ. missing=%s unknown=%s" % (
            sorted(set(EXPECTED_INVARIANTS) - set(invs)), sorted(set(invs) - set(EXPECTED_INVARIANTS))))
        return 1
    print("T27_EXEC PASS: %d tests + %d invariants = %d blocks, %d assertions executed (%s)"
          % (len(tests), len(invs), len(tests) + len(invs), n, os.path.basename(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
