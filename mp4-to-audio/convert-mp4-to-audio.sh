#!/usr/bin/env bash
#
# convert-mp4-to-audio.sh
# ------------------------
# Recursively find every .mp4 file under a folder and convert each one to a
# high-quality audio file placed *right next to the original*, preserving the
# exact subfolder location. After the new audio file is created AND verified,
# the original .mp4 is deleted, and a proof report is printed.
#
# WHY M4A (the default) INSTEAD OF MP3:
#   An .mp4 almost always already contains AAC audio. An .m4a file is the same
#   MPEG-4/AAC container, so the audio can be copied out with NO re-encoding =
#   ZERO quality loss ("remux"). MP3 would force a lossy re-encode and AAC is a
#   better codec than MP3 anyway. So .m4a is both higher quality and less
#   limited. If a file's audio is NOT already AAC/ALAC, it is re-encoded to AAC
#   at 256k (transparent quality). Use --mp3 only if you specifically need MP3.
#
# USAGE:
#   ./convert-mp4-to-audio.sh [options] "/path/to/folder"
#
# OPTIONS:
#   --dry-run     Show what would happen. Convert nothing, delete nothing.
#   --keep        Convert but do NOT delete the original .mp4 files.
#   --mp3         Produce .mp3 (256k) instead of .m4a. (Lower quality; opt-in.)
#   -h, --help    Show this help.
#
# SAFETY: An original .mp4 is deleted ONLY after its new audio file exists, is
#         non-empty, and ffprobe confirms it contains a valid audio stream.
#
set -u

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
DRY_RUN=0
KEEP=0
FORMAT="m4a"
TARGET=""

print_help() { sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --keep)    KEEP=1 ;;
    --mp3)     FORMAT="mp3" ;;
    -h|--help) print_help; exit 0 ;;
    --) shift; TARGET="${1:-}"; ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *)  TARGET="$1" ;;
  esac
  shift
done

if [ -z "$TARGET" ]; then
  echo "Error: no folder given." >&2
  echo "Usage: $0 [--dry-run] [--keep] [--mp3] \"/path/to/folder\"" >&2
  exit 2
fi
if [ ! -d "$TARGET" ]; then
  echo "Error: '$TARGET' is not a folder." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
for bin in ffmpeg ffprobe; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Error: '$bin' not found. Install ffmpeg first:" >&2
    echo "  macOS:         brew install ffmpeg" >&2
    echo "  Ubuntu/Debian: sudo apt-get update && sudo apt-get install ffmpeg" >&2
    echo "  Windows:       winget install Gyan.FFmpeg   (or: choco install ffmpeg)" >&2
    exit 3
  fi
done

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
n_total=0; n_converted=0; n_deleted=0; n_skipped=0; n_failed=0

echo "================================================================"
echo " MP4 -> ${FORMAT^^} conversion"
echo " Folder : $TARGET"
echo " Mode   : $([ $DRY_RUN -eq 1 ] && echo 'DRY RUN (no changes)' || echo 'LIVE')$([ $KEEP -eq 1 ] && echo ' + keep originals')"
echo "================================================================"

# ---------------------------------------------------------------------------
# Process every .mp4 (recursively). -print0 handles spaces/unicode safely.
# ---------------------------------------------------------------------------
while IFS= read -r -d '' src; do
  n_total=$((n_total+1))
  dir=$(dirname "$src")
  base=$(basename "$src")
  stem="${base%.*}"
  out="$dir/$stem.$FORMAT"

  printf '\n[%d] %s\n' "$n_total" "$src"

  # Don't clobber an existing output file.
  if [ -e "$out" ]; then
    echo "    SKIP: target already exists -> $out"
    n_skipped=$((n_skipped+1))
    continue
  fi

  # Probe the source audio codec.
  codec=$(ffprobe -v error -select_streams a:0 \
          -show_entries stream=codec_name -of default=nk=1:nw=1 "$src" </dev/null 2>/dev/null)
  if [ -z "$codec" ]; then
    echo "    SKIP: no audio stream found in this .mp4"
    n_skipped=$((n_skipped+1))
    continue
  fi

  # Decide encoding strategy.
  if [ "$FORMAT" = "m4a" ] && { [ "$codec" = "aac" ] || [ "$codec" = "alac" ]; }; then
    strategy="lossless copy (no re-encode)"
    ff_audio=(-c:a copy)
  elif [ "$FORMAT" = "m4a" ]; then
    strategy="re-encode $codec -> aac 256k"
    ff_audio=(-c:a aac -b:a 256k)
  else
    strategy="re-encode $codec -> mp3 256k"
    ff_audio=(-c:a libmp3lame -b:a 256k)
  fi
  echo "    audio codec: $codec | strategy: $strategy"

  if [ $DRY_RUN -eq 1 ]; then
    echo "    (dry-run) would create: $out"
    echo "    (dry-run) would then delete: $src"
    continue
  fi

  # Convert. -vn drops any video/cover-video stream; metadata (tags) copied.
  if ! ffmpeg -nostdin -v error -y -i "$src" -vn -map_metadata 0 "${ff_audio[@]}" "$out" </dev/null; then
    echo "    FAIL: ffmpeg could not convert. Original left untouched."
    rm -f "$out" 2>/dev/null
    n_failed=$((n_failed+1))
    continue
  fi

  # Verify the new file: exists, non-empty, has a readable audio stream.
  outcodec=$(ffprobe -v error -select_streams a:0 \
             -show_entries stream=codec_name -of default=nk=1:nw=1 "$out" </dev/null 2>/dev/null)
  if [ ! -s "$out" ] || [ -z "$outcodec" ]; then
    echo "    FAIL: output failed verification. Original left untouched."
    rm -f "$out" 2>/dev/null
    n_failed=$((n_failed+1))
    continue
  fi
  n_converted=$((n_converted+1))
  outsize=$(ls -lh "$out" | awk '{print $5}')
  echo "    CREATED: $out ($outsize, audio=$outcodec)  [verified OK]"

  # Delete the original only after successful verification.
  if [ $KEEP -eq 1 ]; then
    echo "    KEPT original (--keep): $src"
    continue
  fi
  rm -f "$src"
  if [ ! -e "$src" ]; then
    n_deleted=$((n_deleted+1))
    echo "    DELETED original: $src  [confirmed gone]"
  else
    echo "    WARNING: could not delete original: $src"
  fi
done < <(find "$TARGET" -type f -iname '*.mp4' -print0)

# ---------------------------------------------------------------------------
# Proof report
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo " SUMMARY"
echo "   .mp4 found      : $n_total"
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
  echo ""
  remaining=$(find "$TARGET" -type f -iname '*.mp4' | wc -l | tr -d ' ')
  echo "PROOF -- .mp4 files still remaining under '$TARGET': $remaining"
  if [ "$remaining" != "0" ]; then
    find "$TARGET" -type f -iname '*.mp4' -print | sed 's/^/   [STILL PRESENT] /'
  else
    echo "   (none -- all converted originals were deleted)"
  fi
fi
