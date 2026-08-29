#!/usr/bin/env bash
#
# Fix your whole Traktor library at once: read collection.nml, and for every
# track beatgrid can analyse, set the exact BPM and put one grid marker on the
# true downbeat. Drifting tracks also get a warped lossless copy in output/.
#
# This is SAFE BY DEFAULT - it does a dry run and never touches your real file
# unless you ask. Recommended order:
#
#   1) See how your paths decode (nothing analysed or written):
#        ./sync-traktor.sh CHECK "~/Documents/Native Instruments/Traktor 3.x/collection.nml"
#
#   2) Dry run on a few tracks (analyses, prints changes, writes nothing):
#        ./sync-traktor.sh DRY  "~/.../collection.nml"   --limit 5
#
#   3) Write the changes to a NEW file (collection.beatgrid.nml, next to yours):
#        ./sync-traktor.sh APPLY "~/.../collection.nml"
#      >>> QUIT TRAKTOR FIRST. Then back up your collection.nml and swap in the
#          new file (or import it). Your original is left alone.
#
# Pass extra flags after the path, e.g.:
#   --limit 20                 only the first 20 matched tracks
#   --only-under ~/Music/DJ    only tracks under that folder
#   --drift skip               don't render warped copies for drifting tracks
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PY="$VENV/bin/python3"

if [ ! -x "$PY" ]; then echo "Run ./setup.sh first." >&2; exit 1; fi
if [ "$#" -lt 2 ]; then
  echo "Usage: ./sync-traktor.sh CHECK|DRY|APPLY <collection.nml> [extra flags]" >&2
  exit 1
fi
MODE="$1"; COLLECTION="$2"; shift 2

case "$MODE" in
  CHECK) FLAGS=(--check) ;;
  DRY)   FLAGS=() ;;
  APPLY) FLAGS=(--apply) ;;
  *) echo "First argument must be CHECK, DRY, or APPLY." >&2; exit 1 ;;
esac

"$PY" "$SCRIPT_DIR/beatgrid.py" nml --collection "$COLLECTION" \
  --out "$SCRIPT_DIR/output" "${FLAGS[@]}" "$@"
