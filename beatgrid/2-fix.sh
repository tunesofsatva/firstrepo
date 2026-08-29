#!/usr/bin/env bash
#
# STEP 2 - FIX THEM.
#
# By default it ONLY corrects BPM + grid numbers inside Traktor - no new files,
# no quality loss, all ratings/comments/cue points kept exactly as they are.
# This fixes WRONG NUMBER tracks and also drifting tracks (their grid is set to
# the best single BPM; a small wander may remain but nothing is re-encoded).
#
# Add WARP only if you want drifting tracks re-timed into brand-new straightened
# copies. Warping re-encodes the audio and costs ~2-3 dB of loudness, so use it
# sparingly, on genuinely wobbly tracks:
#   * "(fixed 123).m4a" copies are written next to each drifting original, with
#     tags/artwork/cue points carried over; a delete-old script is written too.
#
# It always writes collection.beatgrid.nml next to your Traktor collection (your
# real collection.nml is never touched).
#
# Always preview first (writes nothing), then add APPLY:
#   ./2-fix.sh "/Users/you/Music/DJ"                 # preview (numbers only)
#   ./2-fix.sh "/Users/you/Music/DJ" APPLY           # fix the numbers
#   ./2-fix.sh "/Users/you/Music/DJ" APPLY WARP      # also warp drifting tracks
#
# Pass your Traktor collection so it can fix BPMs and carry cue points. QUIT
# TRAKTOR before APPLY (Traktor overwrites its collection when it closes):
#   COLLECTION="$HOME/Documents/Native Instruments/Traktor 3.11.1/collection.nml" \
#     ./2-fix.sh "/Users/you/Music/DJ" APPLY
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$SCRIPT_DIR/.venv/bin/python3"
[ -x "$PY" ] || { echo "Run ./setup.sh first." >&2; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "Run ./setup.sh first (ffmpeg missing)." >&2; exit 1; }
[ "$#" -ge 1 ] || { echo 'Usage: ./2-fix.sh "<folder>" [APPLY] [WARP]' >&2; exit 1; }

# Pull APPLY / WARP keywords out (any order); everything else is a folder.
APPLY=""; WARP=""; FOLDERS=()
for a in "$@"; do
  case "$a" in
    APPLY) APPLY="--apply" ;;
    WARP)  WARP="--warp" ;;
    *)     FOLDERS+=("$a") ;;
  esac
done

# Find your Traktor collection automatically unless you set COLLECTION yourself.
if [ -z "${COLLECTION:-}" ]; then
  COLLECTION="$(ls -t "$HOME/Documents/Native Instruments/"Traktor*/collection.nml 2>/dev/null | head -1 || true)"
  [ -n "$COLLECTION" ] && echo "Using Traktor collection: $COLLECTION"
fi

ARGS=(fix "${FOLDERS[@]}" --out "$SCRIPT_DIR" --drift-ms "${DRIFT_MS:-25}")
[ -n "${COLLECTION:-}" ] && ARGS+=(--collection "$COLLECTION")
[ -n "$APPLY" ] && ARGS+=($APPLY)
[ -n "$WARP" ] && ARGS+=($WARP)
"$PY" "$SCRIPT_DIR/organize.py" "${ARGS[@]}"
