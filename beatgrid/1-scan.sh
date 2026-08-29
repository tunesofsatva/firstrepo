#!/usr/bin/env bash
#
# STEP 1 - LIST WHAT'S WRONG. Changes nothing.
#
# Point it at a folder (or several). It looks at every track and writes ONE
# Excel sheet - beatgrid-report.xlsx, right here in the beatgrid folder -
# labelling each track:
#     GOOD          the grid is fine, leave it alone
#     WRONG NUMBER  steady song, but Traktor's BPM is off (step 2 fixes it)
#     DRIFTS        the tempo wanders, needs a straightened copy (step 2)
#
# Usage:
#   ./1-scan.sh "/Users/you/Music/DJ"
#   ./1-scan.sh "/folder/one" "/folder/two"
#
# To tell WRONG NUMBER apart from GOOD it needs your Traktor collection. Point
# to it once and it remembers nothing - just pass it:
#   COLLECTION="$HOME/Documents/Native Instruments/Traktor 3.11.1/collection.nml" \
#     ./1-scan.sh "/Users/you/Music/DJ"
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$SCRIPT_DIR/.venv/bin/python3"
[ -x "$PY" ] || { echo "Run ./setup.sh first." >&2; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "Run ./setup.sh first (ffmpeg missing)." >&2; exit 1; }
[ "$#" -ge 1 ] || { echo 'Usage: ./1-scan.sh "<folder>" ["<folder2>" ...]' >&2; exit 1; }

ARGS=(scan "$@" --out "$SCRIPT_DIR" --drift-ms "${DRIFT_MS:-25}")
[ -n "${COLLECTION:-}" ] && ARGS+=(--collection "$COLLECTION")
"$PY" "$SCRIPT_DIR/organize.py" "${ARGS[@]}"
echo
echo "Open beatgrid-report.xlsx in this folder to see the full list."
