#!/usr/bin/env bash
#
# STEP 2 - FIX THEM.
#
# WRONG NUMBER tracks -> the BPM + grid is corrected inside Traktor (no new
#                        file, your cue points untouched).
# DRIFTS tracks       -> a straightened lossless copy is written NEXT TO the
#                        original, with tags, artwork and your cue points
#                        carried over. Your original is left alone.
#
# It writes:
#   * collection.beatgrid.nml  - next to your Traktor collection (the corrected
#                                one; your real collection.nml is untouched)
#   * "(fixed 123).m4a" copies - next to each drifting original
#   * delete-old-versions.command - in the beatgrid folder, to run AFTER you've
#                                listened and want to remove the old versions
#
# Always preview first (writes nothing), then add APPLY:
#   ./2-fix.sh "/Users/you/Music/DJ"                 # preview
#   ./2-fix.sh "/Users/you/Music/DJ" APPLY           # do it
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
[ "$#" -ge 1 ] || { echo 'Usage: ./2-fix.sh "<folder>" [APPLY]' >&2; exit 1; }

# Pull a trailing APPLY off the argument list.
APPLY=""
if [ "${!#}" = "APPLY" ]; then APPLY="--apply"; set -- "${@:1:$(($#-1))}"; fi

ARGS=(fix "$@" --out "$SCRIPT_DIR" --drift-ms "${DRIFT_MS:-25}")
[ -n "${COLLECTION:-}" ] && ARGS+=(--collection "$COLLECTION")
[ -n "$APPLY" ] && ARGS+=($APPLY)
"$PY" "$SCRIPT_DIR/organize.py" "${ARGS[@]}"
