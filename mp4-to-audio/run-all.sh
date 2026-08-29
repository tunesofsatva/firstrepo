#!/usr/bin/env bash
#
# run-all.sh
# ----------
# One command that chains the safe steps for a folder:
#   1. CONVERT  every .mp4/.wav -> .m4a (lossless where possible), KEEPING originals.
#   2. RELINK   Traktor collection.nml so your cues/loops/beatgrid/metadata follow
#               each track to its new .m4a  (writes collection_RELINKED.nml; your
#               original collection is never modified).
#   3. STAMP    (optional, --stamp) write the Traktor tags into the .m4a files too,
#               for use OUTSIDE Traktor.
#
# It never deletes anything. After you verify in Traktor, delete the originals
# yourself with:  ./convert-mp4-to-audio.sh --delete-verified "<folder>"
#
# USAGE:
#   ./run-all.sh --collection "/path/collection.nml" [--stamp] [--dry-run] "/music/folder"
#   ./run-all.sh "/music/folder"                 # convert only (no relink/stamp)
#
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

COLLECTION=""; DO_STAMP=0; DRY=""; TARGETS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --collection) shift; COLLECTION="${1:-}" ;;
    --stamp)      DO_STAMP=1 ;;
    --dry-run)    DRY="--dry-run" ;;
    -h|--help)    sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *)  TARGETS+=("$1") ;;
  esac
  shift
done

[ ${#TARGETS[@]} -gt 0 ] || { echo "Error: no folder given (you can pass several)." >&2; exit 2; }
for t in "${TARGETS[@]}"; do
  [ -d "$t" ] || { echo "Error: '$t' is not a folder." >&2; exit 2; }
done
if [ -n "$COLLECTION" ] && [ ! -f "$COLLECTION" ]; then
  echo "Error: collection not found: $COLLECTION" >&2; exit 2
fi

line() { printf '\n============================================================\n'; }

line; echo " STEP 1/3  CONVERT .mp4/.wav -> .m4a  (originals kept)"; line
"$HERE/convert-mp4-to-audio.sh" $DRY "${TARGETS[@]}" || { echo "convert step failed." >&2; exit 1; }

if [ -n "$COLLECTION" ]; then
  line; echo " STEP 2/3  RELINK collection.nml  (cues/loops/grid -> .m4a)"; line
  python3 "$HERE/relink-collection.py" --collection "$COLLECTION" $DRY "${TARGETS[@]}" \
    || { echo "relink step failed." >&2; exit 1; }
else
  line; echo " STEP 2/3  RELINK skipped (no --collection given)"; line
fi

if [ "$DO_STAMP" = "1" ]; then
  if [ -z "$COLLECTION" ]; then
    echo "  --stamp needs --collection; skipping stamp."
  else
    line; echo " STEP 3/3  STAMP Traktor tags into .m4a files"; line
    python3 "$HERE/stamp-from-collection.py" --collection "$COLLECTION" $DRY "${TARGETS[@]}" \
      || { echo "stamp step failed." >&2; exit 1; }
  fi
else
  line; echo " STEP 3/3  STAMP skipped (pass --stamp to enable)"; line
fi

line
echo " DONE. Nothing was deleted."
echo " NEXT:"
if [ -n "$COLLECTION" ]; then
  echo "   1. Quit Traktor, back up your live collection.nml."
  echo "   2. Replace it with collection_RELINKED.nml (rename to collection.nml)."
  echo "   3. Open Traktor, load one .m4a, confirm cues/loops/grid are present."
fi
echo "   4. Once happy, delete the originals by re-running with --delete-verified"
echo "      and the SAME folder(s):"
echo "        $HERE/convert-mp4-to-audio.sh --delete-verified \\"
for t in "${TARGETS[@]}"; do echo "            \"$t\" \\"; done
echo "            # (one line; folders listed above)"
line
