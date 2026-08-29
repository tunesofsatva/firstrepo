#!/usr/bin/env bash
#
# Scan a WHOLE music library (recursively) and report which tracks are out of
# sync (drifting tempo) versus clean (one constant BPM). Writes a spreadsheet
# you can sort: output/library-scan.csv
#
# Usage:
#   ./scan.sh ~/Music/DJ                 # scan a folder and everything under it
#   ./scan.sh                            # default: scan the 'input' folder
#
# Optional settings:
#   DRIFT_MS=15 ./scan.sh ~/Music/DJ     # stricter drift tolerance (default 25)
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -x "$VENV/bin/python3" ]; then
  echo "Python environment missing - run ./setup.sh first." >&2
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is not installed - run ./setup.sh first." >&2
  exit 1
fi

TARGET="${1:-$SCRIPT_DIR/input}"
DRIFT_MS="${DRIFT_MS:-25}"
BPM_MIN="${BPM_MIN:-70}"
BPM_MAX="${BPM_MAX:-180}"

"$VENV/bin/python3" "$SCRIPT_DIR/beatgrid.py" scan "$TARGET" \
  --drift-ms "$DRIFT_MS" --bpm-min "$BPM_MIN" --bpm-max "$BPM_MAX" \
  --out "$SCRIPT_DIR/output"
