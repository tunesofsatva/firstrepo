#!/usr/bin/env bash
#
# Analyse every track in the 'input' folder and print, for each one:
#   * the exact BPM to set in your DJ software (to 3 decimals)
#   * where to anchor the beat grid (the first downbeat)
#   * whether the tempo is CONSTANT (one BPM fixes it) or DRIFTING
#   * if drifting: suggested "reset" cue points, and the warp command
#
# Usage:
#   ./analyze.sh                     # analyse everything in input/
#   ./analyze.sh path/to/track.mp3   # analyse specific file(s)
#
# Optional settings (put in front of the command):
#   DRIFT_MS=15 ./analyze.sh         # stricter: flag drift past 15 ms (default 25)
#   BPM_MIN=60 BPM_MAX=200 ./analyze.sh
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

DRIFT_MS="${DRIFT_MS:-25}"
BPM_MIN="${BPM_MIN:-70}"
BPM_MAX="${BPM_MAX:-180}"

if [ "$#" -gt 0 ]; then
  FILES=("$@")
else
  shopt -s nullglob
  FILES=("$SCRIPT_DIR"/input/*.{mp3,m4a,wav,aiff,aif,flac,aac,mp4,m4v,mov,ogg,wma})
  shopt -u nullglob
fi

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "No audio files found. Put some in the 'input' folder, or pass a path." >&2
  exit 1
fi

"$VENV/bin/python3" "$SCRIPT_DIR/beatgrid.py" analyze \
  --drift-ms "$DRIFT_MS" --bpm-min "$BPM_MIN" --bpm-max "$BPM_MAX" \
  --out "$SCRIPT_DIR/output" "${FILES[@]}"

echo "Reports (.txt and .json per track) saved in the 'output' folder."
