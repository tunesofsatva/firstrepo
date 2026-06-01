#!/usr/bin/env bash
#
# Self-check: proves the whole transcription toolchain actually works.
#
# It generates a short spoken test sentence (using your Mac's built-in voice),
# runs it through the real transcription engine, and confirms the words come
# back. This also downloads the language model the first time, so your first
# real video runs without waiting.
#
# Run it any time:
#   ./selfcheck.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
MODEL="${MODEL:-mlx-community/whisper-large-v3-mlx}"
PHRASE="The quick brown fox jumps over the lazy dog."

echo "=========================================================="
echo " Self-check: verifying your transcription setup"
echo "=========================================================="

# Activate the private Python environment if it exists.
if [ -f "$VENV/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

# --- Tools present? ----------------------------------------------------------
fail() { echo; echo "RESULT: FAILED -- $1"; echo "Try running ./setup.sh again."; exit 1; }

command -v ffmpeg     >/dev/null 2>&1 || fail "ffmpeg is not installed."
command -v mlx_whisper >/dev/null 2>&1 || fail "mlx_whisper is not installed."
echo " [1/4] Tools found (ffmpeg + mlx_whisper)."

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# --- 1) Make a short spoken test clip ----------------------------------------
echo " [2/4] Creating a short spoken test clip..."
if command -v say >/dev/null 2>&1; then
  # macOS: real synthesized speech -> we can verify the words come back.
  say -o "$tmp/speech.aiff" "$PHRASE"
  ffmpeg -nostdin -y -i "$tmp/speech.aiff" -ac 1 -ar 16000 -c:a pcm_s16le \
    "$tmp/test.wav" >/dev/null 2>&1
  SPEECH=1
else
  # Fallback (non-Mac): a plain tone. We can only confirm the engine runs,
  # not that the words match.
  ffmpeg -nostdin -y -f lavfi -i "sine=frequency=440:duration=3" \
    -ac 1 -ar 16000 -c:a pcm_s16le "$tmp/test.wav" >/dev/null 2>&1
  SPEECH=0
fi

# --- 2) Transcribe it (downloads the model on first run) ---------------------
echo " [3/4] Running the transcription engine (first run downloads ~3 GB)..."
mlx_whisper "$tmp/test.wav" \
  --model "$MODEL" \
  --language en \
  --output-dir "$tmp" \
  --output-format txt >/dev/null 2>&1 || fail "the transcription engine errored."

result_txt="$tmp/test.txt"
[ -f "$result_txt" ] || fail "no transcript file was produced."

# --- 3) Judge the result -----------------------------------------------------
echo " [4/4] Checking the result..."
transcript="$(tr '[:upper:]' '[:lower:]' < "$result_txt" | tr -d '\r')"

if [ -z "$(printf '%s' "$transcript" | tr -d '[:space:]')" ]; then
  fail "the transcript came back empty."
fi

echo
echo "----------------------------------------------------------"
echo " Engine output: $(cat "$result_txt")"
echo "----------------------------------------------------------"

if [ "$SPEECH" -eq 1 ]; then
  # Count how many of the test words were recognised.
  hits=0
  for word in quick brown fox jumps lazy dog; do
    case "$transcript" in
      *"$word"*) hits=$((hits + 1)) ;;
    esac
  done
  if [ "$hits" -ge 2 ]; then
    echo
    echo "RESULT: PASSED  (recognised $hits of 6 test words)"
    echo "Your transcription setup is working. You're ready to go!"
    echo "Put a video in 'input' and run ./transcribe.sh"
  else
    fail "the engine ran but the test words were not recognised."
  fi
else
  echo
  echo "RESULT: PASSED (engine ran and produced output)."
  echo "Note: word-accuracy could not be checked on this system because the"
  echo "'say' command is macOS-only. On your Mac it will verify the words too."
fi
