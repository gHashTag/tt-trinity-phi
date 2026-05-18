#!/usr/bin/env bash
#
# check_trinet_specs.sh — TRI-NET spec CI gate.
#
# Verifies:
#   1. Every required numerical claim has a row in
#      docs/VERIFICATION_CLAIMS_MATRIX.md.
#   2. The golden NMSE vector (docs/vectors/nmse/gf16_vs_bfloat16.golden.json)
#      has the required schema fields and is not flagged as SILICON.
#   3. The five required D2D conformance vectors exist and parse.
#   4. The Triple-Decker state-machine spec exists and names the
#      required states.
#   5. If `t27c` is on PATH, run it across specs/numeric/ and
#      specs/fpga/ (best-effort, non-fatal on per-file failure).
#      If `t27c` is absent, skip with a notice.
#
# Exits non-zero on any required-coverage failure. Safe to run locally;
# no network access and no destructive operations.
#
# Usage:
#   scripts/check_trinet_specs.sh           # full check
#   scripts/check_trinet_specs.sh --quiet   # only print errors
#

set -u

QUIET=0
case "${1:-}" in
  --quiet|-q) QUIET=1 ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ----- pretty printers -------------------------------------------------------

FAIL=0
fail() { echo "FAIL: $*" >&2; FAIL=1; }
warn() { echo "WARN: $*" >&2; }
info() { [ "$QUIET" -eq 1 ] || echo "INFO: $*"; }
ok()   { [ "$QUIET" -eq 1 ] || echo "PASS: $*"; }

section() { [ "$QUIET" -eq 1 ] || echo; [ "$QUIET" -eq 1 ] || echo "=== $* ==="; }

# ----- 1. claims matrix existence + required IDs -----------------------------

section "1. VERIFICATION_CLAIMS_MATRIX.md coverage"

MATRIX=docs/VERIFICATION_CLAIMS_MATRIX.md
if [ ! -f "$MATRIX" ]; then
  fail "$MATRIX is missing"
else
  ok "$MATRIX present"
fi

# Required claim IDs (kept in sync with the matrix).
REQUIRED_IDS="
VC-ANCHOR-1 VC-ANCHOR-2 VC-ANCHOR-3 VC-ANCHOR-4
VC-LUCAS-1 VC-LUCAS-2
VC-GF-1 VC-GF-2 VC-GF-3 VC-GF-4
VC-NMSE-1 VC-NMSE-2 VC-NMSE-3 VC-NMSE-4
VC-D2D-1 VC-D2D-2 VC-D2D-3 VC-D2D-4 VC-D2D-5
VC-DECK-1 VC-DECK-2 VC-DECK-3 VC-DECK-4
VC-22FDX-1 VC-22FDX-2 VC-22FDX-3
VC-CELL-1 VC-CELL-2
VC-NM-1 VC-NM-2 VC-NM-3 VC-NM-4 VC-NM-5 VC-NM-6
"

if [ -f "$MATRIX" ]; then
  for id in $REQUIRED_IDS; do
    if ! grep -q "$id" "$MATRIX"; then
      fail "claim $id missing from $MATRIX"
    fi
  done
  [ "$FAIL" -eq 0 ] && ok "all required claim IDs present in matrix"
fi

# ----- 2. golden NMSE vector -------------------------------------------------

section "2. Golden NMSE vector (GF16 vs bfloat16)"

NMSE_JSON=docs/vectors/nmse/gf16_vs_bfloat16.golden.json
if [ ! -f "$NMSE_JSON" ]; then
  fail "$NMSE_JSON is missing"
else
  ok "$NMSE_JSON present"

  python3 - "$NMSE_JSON" <<'PY' || fail "NMSE golden vector schema check failed"
import json, sys
p = sys.argv[1]
with open(p) as f:
    d = json.load(f)

errors = []

def need(cond, msg):
    if not cond:
        errors.append(msg)

need(d.get("protocol") == "GF16_BFLOAT16_NMSE/1.0", "protocol mismatch")
need(d.get("sample_count") == 1048576, "sample_count must be 1048576")
need(d.get("seed") == "0x47C0", "seed must be '0x47C0'")
need(d.get("provenance", {}).get("mode") != "SILICON",
     "R5 honesty: provenance.mode must not be 'SILICON' for golden vector")
need(d.get("provenance", {}).get("silicon") is False,
     "R5 honesty: provenance.silicon must be false for golden vector")

dist_ids = {x["id"] for x in d.get("distributions", [])}
for needed in ("D-1", "D-2", "D-3", "D-4", "D-5", "D-6"):
    need(needed in dist_ids, f"distribution {needed} missing")

formats = {f["name"] for f in d.get("formats", [])}
need("gf16" in formats and "bfloat16" in formats, "formats must include gf16 and bfloat16")

# Every (dist, format) pair has a baseline with finite nmse_db and positive tolerance.
seen = set()
for r in d.get("results", []):
    seen.add((r.get("dist"), r.get("format")))
    e = r.get("expected", {})
    need(isinstance(e.get("nmse_db"), (int, float)), f"non-numeric nmse_db for {r}")
    need(isinstance(e.get("tolerance_db"), (int, float)) and e["tolerance_db"] > 0,
         f"non-positive tolerance_db for {r}")

for did in ("D-1", "D-2", "D-3", "D-4", "D-5", "D-6"):
    for fmt in ("gf16", "bfloat16"):
        need((did, fmt) in seen, f"missing result for ({did}, {fmt})")

if errors:
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("  golden NMSE vector schema OK")
PY
fi

# ----- 3. D2D conformance vectors --------------------------------------------

section "3. D2D conformance vectors"

D2D_REQUIRED="valid_header.json bad_crc.json unsupported_opcode.json timeout_retry.json multi_chip_ordering.json"
for f in $D2D_REQUIRED; do
  p="conformance/d2d/$f"
  if [ ! -f "$p" ]; then
    fail "missing required D2D vector: $p"
  else
    ok "found $p"
    python3 -c "
import json, sys
with open('$p') as fh:
    d = json.load(fh)
required = ['scenario_id', 'scenario_name', 'claims_matrix_rows', 'expected_outcome', 'frames']
missing = [k for k in required if k not in d]
if missing:
    print('  missing keys in $p:', missing); sys.exit(1)
" || fail "schema check failed for $p"
  fi
done

# Cross-link: every claims_matrix_rows entry referenced by D2D vectors must exist in the matrix.
if [ -f "$MATRIX" ]; then
  for f in $D2D_REQUIRED; do
    p="conformance/d2d/$f"
    [ -f "$p" ] || continue
    python3 - "$p" "$MATRIX" <<'PY' || fail "D2D vector references unknown VC- id"
import json, sys, re
p, matrix = sys.argv[1], sys.argv[2]
with open(p) as fh:
    d = json.load(fh)
with open(matrix) as fh:
    text = fh.read()
ids = d.get("claims_matrix_rows", [])
missing = [i for i in ids if i not in text]
if missing:
    print(f"  {p} references unknown ids:", missing)
    sys.exit(1)
PY
  done
fi

# ----- 4. Triple-Decker state-machine spec -----------------------------------

section "4. Triple-Decker state-machine spec"

DECK_DOC=docs/TRIPLE_DECKER_STATE_MACHINE.md
if [ ! -f "$DECK_DOC" ]; then
  fail "$DECK_DOC missing"
else
  ok "$DECK_DOC present"
  for state in IDLE RBB FBB CAP_BOOST BROWNOUT; do
    if ! grep -qw "$state" "$DECK_DOC"; then
      fail "$DECK_DOC missing state '$state'"
    fi
  done
  for word in cooldown brownout overcurrent; do
    if ! grep -qi "$word" "$DECK_DOC"; then
      fail "$DECK_DOC missing required keyword '$word'"
    fi
  done
fi

# ----- 5. t27c parse (best-effort) -------------------------------------------

section "5. t27c parse (optional)"

if command -v t27c >/dev/null 2>&1; then
  info "t27c found at $(command -v t27c)"
  T27_FAIL=0
  for d in specs/numeric specs/fpga; do
    [ -d "$d" ] || continue
    for f in "$d"/*.t27; do
      [ -f "$f" ] || continue
      if ! t27c --check "$f" >/dev/null 2>&1; then
        # Don't fail the gate on a single bad t27 — t27c versions vary.
        warn "t27c parse failed: $f"
        T27_FAIL=$((T27_FAIL+1))
      fi
    done
  done
  if [ "$T27_FAIL" -eq 0 ]; then
    ok "t27c parsed all specs cleanly"
  else
    warn "t27c reported $T27_FAIL parse failures (non-fatal)"
  fi
else
  info "t27c not on PATH — skipping (safe; gate continues)"
fi

# ----- 6. Cross-doc claim presence -------------------------------------------
#
# Any numerical claim that lands in another doc and is meant to be governed
# by this gate must reference a VC- id. We don't enforce that every number
# in every doc has an ID (too noisy), but we DO check that the key docs
# that already cite VC- ids only cite known ones.

section "6. Cross-doc VC- citations"

if [ -f "$MATRIX" ]; then
  KNOWN_IDS=$(grep -oE 'VC-[A-Z]+-[0-9]+' "$MATRIX" | sort -u)
  for doc in BENCHMARKS.md STATUS.md D2D_PROTOCOL.md GF16_BFLOAT16_NMSE.md \
             TRIPLE_DECK_STATUS.md TOPS_W_22FDX_PROJECTION.md \
             docs/TRIPLE_DECKER_STATE_MACHINE.md; do
    [ -f "$doc" ] || continue
    CITED=$(grep -oE 'VC-[A-Z]+-[0-9]+' "$doc" 2>/dev/null | sort -u)
    [ -z "$CITED" ] && continue
    for id in $CITED; do
      if ! echo "$KNOWN_IDS" | grep -qx "$id"; then
        fail "$doc cites unknown claim id $id"
      fi
    done
  done
  ok "VC- citations across key docs resolve to known ids"
fi

# ----- summary ---------------------------------------------------------------

echo
if [ "$FAIL" -eq 0 ]; then
  echo "OK: TRI-NET spec gate passed."
  exit 0
else
  echo "FAIL: TRI-NET spec gate failed. See messages above."
  exit 1
fi
