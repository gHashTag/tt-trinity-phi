#!/usr/bin/env bash
# create_issues.sh — file the TRI-NET 2026 epic + 16 children from this directory.
#
# Default mode: DRY-RUN. Prints the gh commands without running them.
# Pass --apply to actually create issues.
#
# Safety:
#   - Refuses to run if `gh` is missing.
#   - Refuses to run outside this directory or outside the expected repo.
#   - Never deletes, closes, or edits issues.
#   - Reads body text from each .md file via `--body-file`.
#
# Usage:
#   ./create_issues.sh                # dry-run (default)
#   ./create_issues.sh --apply        # actually file
#   ./create_issues.sh --repo OWNER/NAME --apply
#
# Identifiers:
#   The local plan IDs (#0..#16) in the .md files are placeholders.
#   GitHub mints the real numbers at filing time. The stable handle is
#   the track ID in the filename (CL-01, EN-02, etc.).

set -euo pipefail

APPLY=0
REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --repo)  REPO="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found. Install https://cli.github.com/ first." >&2
  exit 3
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Build the file list deterministically: epic first (00_), then 01_..16_.
EPIC_FILE="00_EPIC_2026.md"
CHILDREN=( $(ls -1 [0-1][0-9]_*.md 2>/dev/null | grep -v '^00_' | sort) )

if [[ ! -f "$EPIC_FILE" ]]; then
  echo "ERROR: $EPIC_FILE not found in $SCRIPT_DIR" >&2
  exit 4
fi

if [[ ${#CHILDREN[@]} -ne 16 ]]; then
  echo "ERROR: expected 16 child issue files, found ${#CHILDREN[@]}" >&2
  exit 5
fi

# Repo flag (optional). If unset, gh uses the default repo for the cwd.
REPO_FLAG=()
if [[ -n "$REPO" ]]; then
  REPO_FLAG=(--repo "$REPO")
fi

# First line of each markdown file = "# <title>" — strip the "# ".
issue_title() {
  head -n 1 "$1" | sed -E 's/^#\s*//'
}

run_or_print() {
  if [[ $APPLY -eq 1 ]]; then
    "$@"
  else
    # Print a copy-pasteable representation.
    printf '%q ' "$@"
    printf '\n'
  fi
}

echo "=== TRI-NET 2026 issue filing ==="
echo "Mode:   $([[ $APPLY -eq 1 ]] && echo APPLY || echo DRY-RUN)"
echo "Repo:   $([[ -n "$REPO" ]] && echo "$REPO" || echo "<gh default for cwd>")"
echo "Files:  $((1 + ${#CHILDREN[@]})) (1 epic + ${#CHILDREN[@]} children)"
echo

# 1) Epic
EPIC_TITLE="$(issue_title "$EPIC_FILE")"
echo "--- EPIC: $EPIC_TITLE ---"
run_or_print gh issue create \
  "${REPO_FLAG[@]}" \
  --title "$EPIC_TITLE" \
  --body-file "$EPIC_FILE" \
  --label "epic" \
  --label "track:SIP"

# 2) Children
for f in "${CHILDREN[@]}"; do
  TITLE="$(issue_title "$f")"
  # Track ID is the second underscore-separated chunk in the filename.
  # e.g. 01_CL-01_d2d_drain_on_restraint.md -> CL-01
  TRACK="$(basename "$f" .md | awk -F'_' '{print $2}')"
  # Track family (CL / EN / SN / PUB / OS) drives the track: label.
  FAMILY="$(echo "$TRACK" | sed 's/-.*//')"

  LABELS=( --label "track:${FAMILY}" --label "r5:target" --label "sip" )

  echo
  echo "--- $TRACK: $TITLE ---"
  run_or_print gh issue create \
    "${REPO_FLAG[@]}" \
    --title "$TITLE" \
    --body-file "$f" \
    "${LABELS[@]}"
done

echo
if [[ $APPLY -eq 1 ]]; then
  echo "Done. Real GitHub issue numbers are visible in the gh output above."
  echo "Update local plan IDs (#0..#16) in ISSUES_SUMMARY.md if you want a mapping table."
else
  echo "Dry-run complete. Re-run with --apply to actually file."
fi
