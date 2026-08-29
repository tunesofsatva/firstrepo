#!/usr/bin/env bash
#
# Render a NEW lossless copy of a track whose beats are warped onto a perfectly
# even grid, so any DJ software lines up at ONE constant BPM for the whole song.
# The original file is never touched; the new file lands in the 'output' folder.
#
# Usage:
#   ./warp.sh input/track.mp3 128       # warp to exactly 128.00 BPM
#   ./warp.sh input/track.mp3           # warp to the BPM beatgrid detects
#
# Needs rubberband (setup.sh installs it; or: brew install rubberband).
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -x "$VENV/bin/python3" ]; then
  echo "Python environment missing - run ./setup.sh first." >&2
  exit 1
fi
if [ "$#" -lt 1 ]; then
  echo "Usage: ./warp.sh <file> [target-bpm]" >&2
  exit 1
fi
FILE="$1"
BPM="${2:-}"

ARGS=("$SCRIPT_DIR/beatgrid.py" warp "$FILE" --out "$SCRIPT_DIR/output")
[ -n "$BPM" ] && ARGS+=(--bpm "$BPM")

"$VENV/bin/python3" "${ARGS[@]}"
echo "Done. The warped file is a lossless WAV in the 'output' folder."
echo "Import it, set the BPM to your target, anchor the grid on beat 1 - done."
