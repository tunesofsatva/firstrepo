#!/usr/bin/env bash
#
# Download YouTube videos as audio files, ready to transcribe.
#
# For transcription we only need the audio, so this grabs the audio track
# (much smaller and faster than the full video) and saves it into the 'input'
# folder. After it finishes, just run ./transcribe.sh as usual.
#
# Two ways to use it:
#
#   1) Paste your links into the file 'youtube-urls.txt' (one per line), then:
#        ./download.sh
#
#   2) Or pass links directly on the command line:
#        ./download.sh "https://youtu.be/XXXX" "https://youtu.be/YYYY"
#
# Playlists work too - paste a playlist link and every video is downloaded.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$SCRIPT_DIR/input"
VENV="$SCRIPT_DIR/.venv"
URLS_FILE="$SCRIPT_DIR/youtube-urls.txt"

mkdir -p "$INPUT_DIR"

# Use the private Python environment if present.
if [ -f "$VENV/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "ERROR: yt-dlp is not installed. Run ./setup.sh first." >&2
  exit 1
fi

# --- Gather the list of links -------------------------------------------------
urls=()
if [ "$#" -gt 0 ]; then
  # Links passed on the command line.
  for u in "$@"; do urls+=("$u"); done
elif [ -f "$URLS_FILE" ]; then
  # Links from youtube-urls.txt (ignore blank lines and lines starting with #).
  while IFS= read -r line || [ -n "$line" ]; do
    trimmed="$(printf '%s' "$line" | awk '{$1=$1; print}')"
    [ -z "$trimmed" ] && continue
    case "$trimmed" in \#*) continue ;; esac
    urls+=("$trimmed")
  done < "$URLS_FILE"
fi

if [ "${#urls[@]}" -eq 0 ]; then
  echo "No YouTube links found."
  echo
  echo "Either:"
  echo "  - open 'youtube-urls.txt', paste your links (one per line), save,"
  echo "    then run ./download.sh again, or"
  echo "  - run:  ./download.sh \"https://youtu.be/your-link\""
  exit 0
fi

echo "=========================================================="
echo " Downloading audio for ${#urls[@]} link(s) into: input/"
echo "=========================================================="

# Optional: borrow your browser's YouTube login to clear stubborn 403 errors.
# Run like:  COOKIES_FROM_BROWSER=safari ./download.sh
# (also works with: chrome, firefox, edge, brave)
cookie_args=()
if [ -n "${COOKIES_FROM_BROWSER:-}" ]; then
  echo " Using login from your $COOKIES_FROM_BROWSER browser."
  cookie_args=(--cookies-from-browser "$COOKIES_FROM_BROWSER")
fi

# -f ...                : prefer best audio-only; fall back to best available
# --restrict-filenames  : produce safe filenames (no spaces/odd characters)
# --no-overwrites       : skip anything already sitting in the input folder
# --ignore-errors       : keep going if one link fails
# --remote-components    : let yt-dlp fetch YouTube's JS challenge solver
#                         (run by Deno) so signed download links work
yt-dlp \
  -f "bestaudio/bestaudio*/best" \
  --restrict-filenames \
  --no-overwrites \
  --ignore-errors \
  --remote-components ejs:github \
  ${cookie_args[@]+"${cookie_args[@]}"} \
  -o "$INPUT_DIR/%(title)s.%(ext)s" \
  ${urls[@]+"${urls[@]}"}

echo
echo "=========================================================="
echo " Download complete. Files are in the 'input' folder."
echo
echo " Next step:  ./transcribe.sh"
echo "=========================================================="
