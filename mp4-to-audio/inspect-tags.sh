#!/usr/bin/env bash
#
# inspect-tags.sh
# ----------------
# Show ALL metadata tags in your audio/video files so you can verify what
# Traktor actually wrote into the FILE (vs. what only lives in collection.nml),
# and confirm what survived a conversion.
#
# Give it a single file, OR a folder. For a folder, every .mp4/.wav that has a
# .m4a sibling is shown as a BEFORE (original) / AFTER (converted) pair so you
# can eyeball exactly which fields carried over (Rating, Comment 2, BPM, Key…).
#
# It uses `exiftool` if installed (best — reads Traktor's proprietary atoms),
# otherwise falls back to `ffprobe`. Install exiftool for the fullest picture:
#   macOS: brew install exiftool
#
# USAGE:
#   ./inspect-tags.sh "/path/to/file.m4a"
#   ./inspect-tags.sh "/path/to/folder"
#
set -u

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "Usage: $0 \"/path/to/file-or-folder\"" >&2
  exit 2
fi

if command -v exiftool >/dev/null 2>&1; then
  DUMP() { exiftool -G1 -a -s -- "$1" 2>/dev/null; }
  TOOL="exiftool"
elif command -v ffprobe >/dev/null 2>&1; then
  DUMP() { ffprobe -hide_banner -i "$1" 2>&1 | sed -n '/Metadata:/,/Duration:/p'; }
  TOOL="ffprobe (install exiftool for full tag visibility)"
else
  echo "Error: need exiftool or ffprobe installed." >&2
  exit 3
fi
echo "Tag reader: $TOOL"

show_one() {
  echo "==================================================================="
  echo "FILE: $1"
  echo "-------------------------------------------------------------------"
  DUMP "$1"
  echo ""
}

show_pair() {
  local src="$1" dir base stem m4a
  dir=$(dirname "$src"); base=$(basename "$src"); stem="${base%.*}"
  m4a="$dir/$stem.m4a"
  echo "==================================================================="
  echo "TRACK: $stem"
  echo "----- BEFORE (original: $base) ------------------------------------"
  DUMP "$src"
  if [ -e "$m4a" ]; then
    echo "----- AFTER  (converted: $stem.m4a) -------------------------------"
    DUMP "$m4a"
  else
    echo "----- AFTER: no converted .m4a sibling found yet -----------------"
  fi
  echo ""
}

if [ -f "$TARGET" ]; then
  show_one "$TARGET"
elif [ -d "$TARGET" ]; then
  found=0
  while IFS= read -r -d '' src; do
    found=1; show_pair "$src"
  done < <(find "$TARGET" -type f \( -iname '*.mp4' -o -iname '*.wav' \) -print0)
  if [ "$found" = "0" ]; then
    # No originals left (already deleted) -> just dump the .m4a files.
    while IFS= read -r -d '' f; do show_one "$f"; done \
      < <(find "$TARGET" -type f -iname '*.m4a' -print0)
  fi
else
  echo "Error: '$TARGET' is neither a file nor a folder." >&2
  exit 2
fi
