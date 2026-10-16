#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed check of a cocotb results.xml.

A green `make` is not accepted on its own. This requires that
  * results.xml exists and parses,
  * the testcases present are EXACTLY the @cocotb.test() functions declared in test/test.py
    (a test that crashed before starting, or was silently dropped, fails here),
  * no testcase has a <failure>, <error> or <skipped> child.
Usage: python3 test/check_results.py [results.xml] [test.py]
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))


def declared_tests(path):
    with open(path) as f:
        text = f.read()
    return sorted(re.findall(r"@cocotb\.test\([^)]*\)\s*\nasync def (test_\w+)", text))


def load(path):
    tree = ET.parse(path)
    cases = []
    for tc in tree.getroot().iter("testcase"):
        bad = [c.tag for c in tc if c.tag in ("failure", "error", "skipped")]
        cases.append((tc.get("name"), bad, ET.tostring(tc, encoding="unicode")))
    return cases


def main(argv):
    results = argv[1] if len(argv) > 1 else os.path.join(HERE, "results.xml")
    test_py = argv[2] if len(argv) > 2 else os.path.join(HERE, "test.py")
    if not os.path.isfile(results):
        print("CHECK_RESULTS FAIL: %s does not exist" % results)
        return 1
    want = declared_tests(test_py)
    if not want:
        print("CHECK_RESULTS FAIL: no @cocotb.test found in %s" % test_py)
        return 1
    try:
        cases = load(results)
    except ET.ParseError as e:
        print("CHECK_RESULTS FAIL: results.xml does not parse: %s" % e)
        return 1
    got = sorted(c[0] for c in cases)
    if got != want:
        print("CHECK_RESULTS FAIL: executed tests differ. missing=%s unexpected=%s"
              % (sorted(set(want) - set(got)), sorted(set(got) - set(want))))
        return 1
    bad = [(n, b) for (n, b, _) in cases if b]
    if bad:
        print("CHECK_RESULTS FAIL: %d of %d tests failed: %s" % (len(bad), len(cases), bad))
        return 1
    print("CHECK_RESULTS PASS: %d of %d tests executed and passed" % (len(cases), len(want)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
