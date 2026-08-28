#!/usr/bin/env bash
#
# convert-mp4-to-audio.sh
# ------------------------
# Recursively convert .mp4 (and .wav) files under a folder into high-quality
# .m4a audio, each placed RIGHT NEXT TO its original (same subfolder, any depth).
# By default NOTHING is deleted -- you verify the results (e.g. Traktor cue
# points) first, then run again with --delete-verified to remove the originals.
#
# QUALITY / CODEC CHOICE (the goal: highest quality, least loss):
#   * .mp4 with AAC/ALAC audio -> copied out with NO re-encode  = ZERO loss.
#   * .wav (PCM) / .flac / lossless -> encoded to ALAC (lossless) in .m4a
#                                       = ZERO loss, ~40-60% smaller than WAV.
#   * other lossy audio (mp3, ac3, opus, ...) -> re-encoded to AAC 256k.
#   .m4a is chosen over .mp3 because it holds both AAC and ALAC losslessly and
#   is a stronger, less-limited format. (--mp3 forces lossy MP3 if you insist.)
#
# TRAKTOR / METADATA NOTE:
#   Standard tags (title, artist, genre, bpm, comment) are carried over.
#   Traktor CUE POINTS / BEATGRIDS often live in Traktor's collection.nml, not
#   in the file, and any embedded copy is a proprietary tag that may NOT survive
#   a container change. So: BACK UP collection.nml, convert (keeping originals),
#   check one track in Traktor, and only then --delete-verified.
#
# USAGE:
#   ./convert-mp4-to-audio.sh [options] "/path/to/folder"
#
# OPTIONS:
#   (no flag)          Convert everything, KEEP all originals (safe default).
#   --delete-verified  Do NOT convert. Delete each .mp4/.wav that already has a
#                      valid .m4a sibling next to it. Prints a proof report.
#   --delete           Convert AND delete each original immediately after its
#                      new file is verified (one-shot; skips the safety pause).
#   --dry-run          Show what would happen. Change nothing.
#   --mp3              Produce lossy .mp3 (256k) instead of .m4a. Discouraged.
#   -h, --help         Show this help.
#
set -u

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
DRY_RUN=0
MODE="convert"        # convert | delete-verified
DELETE_NOW=0
FORMAT="m4a"
TARGET=""

print_help() { sed -n '2,52p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)         DRY_RUN=1 ;;
    --delete-verified) MODE="delete-verified" ;;
    --delete)          DELETE_NOW=1 ;;
    --mp3)             FORMAT="mp3" ;;
    -h|--help)         print_help; exit 0 ;;
    --) shift; TARGET="${1:-}" ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *)  TARGET="$1" ;;
  esac
  shift
done

if [ -z "$TARGET" ]; then
  echo "Error: no folder given." >&2
  echo "Usage: $0 [--delete-verified|--delete|--dry-run|--mp3] \"/path/to/folder\"" >&2
  exit 2
fi
if [ ! -d "$TARGET" ]; then
  echo "Error: '$TARGET' is not a folder." >&2
  exit 2
fi

for bin in ffmpeg ffprobe; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Error: '$bin' not found. Install ffmpeg first:" >&2
    echo "  macOS:         brew install ffmpeg" >&2
    echo "  Ubuntu/Debian: sudo apt-get update && sudo apt-get install ffmpeg" >&2
    exit 3
  fi
done

# Return the first audio codec name of a file (empty if none / unreadable).
audio_codec() {
  ffprobe -v error -select_streams a:0 -show_entries stream=codec_name \
          -of default=nk=1:nw=1 "$1" </dev/null 2>/dev/null
}

# ===========================================================================
# MODE: delete-verified  (delete originals that already have a valid .m4a)
# ===========================================================================
if [ "$MODE" = "delete-verified" ]; then
  n_total=0; n_deleted=0; n_kept=0
  echo "== DELETE-VERIFIED under: $TARGET =="
  while IFS= read -r -d '' src; do
    n_total=$((n_total+1))
    dir=$(dirname "$src"); base=$(basename "$src"); stem="${base%.*}"
    printf '\n[%d] %s\n' "$n_total" "$src"
    sibling=""
    for ext in m4a mp3; do
      cand="$dir/$stem.$ext"
      if [ -s "$cand" ] && [ -n "$(audio_codec "$cand")" ]; then sibling="$cand"; break; fi
    done
    if [ -z "$sibling" ]; then
      echo "    KEEP: no verified audio sibling found -> not deleting"
      n_kept=$((n_kept+1)); continue
    fi
    echo "    verified sibling: $sibling"
    if [ $DRY_RUN -eq 1 ]; then echo "    (dry-run) would delete: $src"; continue; fi
    rm -f "$src"
    if [ ! -e "$src" ]; then echo "    DELETED: $src  [confirmed gone]"; n_deleted=$((n_deleted+1));
    else echo "    WARNING: could not delete $src"; fi
  done < <(find "$TARGET" -type f \( -iname '*.mp4' -o -iname '*.wav' \) -print0)
  echo ""
  echo "== SUMMARY == originals found: $n_total | deleted: $n_deleted | kept: $n_kept"
  echo ""
  echo "PROOF -- .mp4/.wav still remaining under '$TARGET':"
  rem=$(find "$TARGET" -type f \( -iname '*.mp4' -o -iname '*.wav' \) | wc -l | tr -d ' ')
  echo "   count: $rem"
  find "$TARGET" -type f \( -iname '*.mp4' -o -iname '*.wav' \) -print | sed 's/^/   [STILL PRESENT] /'
  exit 0
fi

# ===========================================================================
# MODE: convert
# ===========================================================================
n_total=0; n_converted=0; n_deleted=0; n_skipped=0; n_failed=0

echo "================================================================"
echo " Convert .mp4/.wav -> ${FORMAT^^}"
echo " Folder : $TARGET"
if [ $DRY_RUN -eq 1 ]; then mode_desc="DRY RUN (no changes)";
elif [ $DELETE_NOW -eq 1 ]; then mode_desc="LIVE + delete originals after verify";
else mode_desc="LIVE (keep all originals)"; fi
echo " Mode   : $mode_desc"
echo "================================================================"

while IFS= read -r -d '' src; do
  n_total=$((n_total+1))
  dir=$(dirname "$src"); base=$(basename "$src"); stem="${base%.*}"
  out="$dir/$stem.$FORMAT"
  printf '\n[%d] %s\n' "$n_total" "$src"

  if [ -e "$out" ]; then
    echo "    SKIP: target already exists -> $out"
    n_skipped=$((n_skipped+1)); continue
  fi

  codec=$(audio_codec "$src")
  if [ -z "$codec" ]; then
    echo "    SKIP: no audio stream found"
    n_skipped=$((n_skipped+1)); continue
  fi

  # Decide strategy (preserve quality; never upconvert a lossy source to ALAC).
  if [ "$FORMAT" = "mp3" ]; then
    strategy="re-encode $codec -> mp3 256k (LOSSY)"; ff_audio=(-c:a libmp3lame -b:a 256k)
  else
    case "$codec" in
      aac|alac)
        strategy="lossless copy ($codec, no re-encode)"; ff_audio=(-c:a copy) ;;
      pcm_*|flac|wavpack|tta|truehd|mlp)
        strategy="lossless encode $codec -> ALAC"; ff_audio=(-c:a alac) ;;
      *)
        strategy="re-encode $codec -> aac 256k"; ff_audio=(-c:a aac -b:a 256k) ;;
    esac
  fi
  echo "    audio codec: $codec | strategy: $strategy"

  if [ $DRY_RUN -eq 1 ]; then
    echo "    (dry-run) would create: $out"
    [ $DELETE_NOW -eq 1 ] && echo "    (dry-run) would then delete: $src"
    continue
  fi

  # -vn drops any video/cover-video; metadata carried best-effort.
  if ! ffmpeg -nostdin -v error -y -i "$src" -vn -map_metadata 0 \
        -movflags use_metadata_tags "${ff_audio[@]}" "$out" </dev/null; then
    echo "    FAIL: ffmpeg could not convert. Original untouched."
    rm -f "$out" 2>/dev/null; n_failed=$((n_failed+1)); continue
  fi

  outcodec=$(audio_codec "$out")
  if [ ! -s "$out" ] || [ -z "$outcodec" ]; then
    echo "    FAIL: output failed verification. Original untouched."
    rm -f "$out" 2>/dev/null; n_failed=$((n_failed+1)); continue
  fi
  n_converted=$((n_converted+1))
  outsize=$(ls -lh "$out" | awk '{print $5}')
  echo "    CREATED: $out ($outsize, audio=$outcodec)  [verified OK]"

  if [ $DELETE_NOW -eq 1 ]; then
    rm -f "$src"
    if [ ! -e "$src" ]; then n_deleted=$((n_deleted+1)); echo "    DELETED original: $src  [confirmed gone]";
    else echo "    WARNING: could not delete original: $src"; fi
  else
    echo "    KEPT original (verify in Traktor, then run --delete-verified): $src"
  fi
done < <(find "$TARGET" -type f \( -iname '*.mp4' -o -iname '*.wav' \) -print0)

echo ""
echo "================================================================"
echo " SUMMARY"
echo "   sources found   : $n_total"
echo "   converted       : $n_converted"
echo "   originals deleted: $n_deleted"
echo "   skipped         : $n_skipped"
echo "   failed          : $n_failed"
echo "================================================================"

if [ $DRY_RUN -eq 0 ] && [ $n_total -gt 0 ]; then
  echo ""
  echo "PROOF -- audio files now present under '$TARGET':"
  find "$TARGET" -type f \( -iname '*.m4a' -o -iname '*.mp3' \) -print0 \
    | xargs -0 -r ls -lh 2>/dev/null | awk '{print "   [KEPT] "$5"\t"$NF}'
  if [ $DELETE_NOW -eq 0 ]; then
    echo ""
    echo "NOTE: originals were KEPT. After you confirm cues/metadata in Traktor,"
    echo "      delete them safely with:"
    echo "      $0 --delete-verified \"$TARGET\""
  fi
fi
