#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fetch ONE pinned Zig release from the official vendor and verify it, fail closed.

The version, the x86_64-linux tarball URL, its size and its SHA-256 are taken from the
official index https://ziglang.org/download/index.json. The downloaded file must match both
size and digest, the URL must be on ziglang.org, and the unpacked compiler must report exactly
the requested version. The verified version, URL, size and digest are printed.

Nothing is installed system-wide and no existing Zig is replaced: the compiler is unpacked
into --dest, and (when --path-file is given, e.g. $GITHUB_PATH) that directory is PREPENDED to
PATH for the remaining steps of the current job only.

Usage: python3 test/fetch_zig.py --version 0.16.0 --dest "$RUNNER_TEMP/zig" --path-file "$GITHUB_PATH"
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.request

INDEX = "https://ziglang.org/download/index.json"
PLATFORM = "x86_64-linux"


def fail(msg):
    print("FETCH_ZIG FAIL: " + msg)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--path-file", default=None)
    args = ap.parse_args()

    with urllib.request.urlopen(INDEX, timeout=60) as r:
        index = json.load(r)
    if args.version not in index:
        fail("version %s is not in %s" % (args.version, INDEX))
    entry = index[args.version].get(PLATFORM)
    if not entry:
        fail("no %s entry for %s in the official index" % (PLATFORM, args.version))
    url, want_sha, want_size = entry.get("tarball"), entry.get("shasum"), entry.get("size")
    if not url or not want_sha or not want_size:
        fail("index entry lacks tarball/shasum/size: %s" % entry)
    if not url.startswith("https://ziglang.org/"):
        fail("tarball URL is not on ziglang.org: %s" % url)
    want_size = int(want_size)

    os.makedirs(args.dest, exist_ok=True)
    tarball = os.path.join(args.dest, os.path.basename(url))
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url, timeout=300) as r, open(tarball, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    got_sha = digest.hexdigest()
    if size != want_size:
        fail("size %d != index size %d" % (size, want_size))
    if got_sha != want_sha:
        fail("sha256 %s != index shasum %s" % (got_sha, want_sha))

    with tarfile.open(tarball, "r:xz") as tf:
        names = tf.getnames()
        top = sorted({n.split("/")[0] for n in names if n and not n.startswith("/") and ".." not in n})
        if len(top) != 1:
            fail("tarball does not have exactly one top-level directory: %s" % top)
        tf.extractall(args.dest, filter="data")
    zdir = os.path.join(args.dest, top[0])
    zig = os.path.join(zdir, "zig")
    if not os.path.isfile(zig):
        fail("no zig executable at %s" % zig)
    ver = subprocess.run([zig, "version"], capture_output=True, text=True)
    if ver.returncode != 0 or ver.stdout.strip() != args.version:
        fail("unpacked zig reports %r (rc=%d), expected %s" % (ver.stdout.strip(), ver.returncode, args.version))

    print("zig version : %s" % ver.stdout.strip())
    print("tarball     : %s" % url)
    print("size        : %d" % size)
    print("sha256      : %s  (equals the official index shasum)" % got_sha)
    print("directory   : %s" % zdir)
    if args.path_file:
        with open(args.path_file, "a") as f:
            f.write(zdir + "\n")
        print("prepended to PATH for the rest of this job only (system Zig untouched)")
    print("FETCH_ZIG PASS")


if __name__ == "__main__":
    main()
