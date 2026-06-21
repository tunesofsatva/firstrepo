#!/usr/bin/env bash
#
# One-time setup for the local transcription workflow (Apple Silicon Macs).
#
# It installs the two tools we need and nothing else:
#   * ffmpeg     - reads your video files and extracts the audio
#   * mlx-whisper - Apple's GPU-accelerated speech-to-text engine
#
# Run it once:
#   ./setup.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

echo "=========================================================="
echo " Setting up your local transcription workflow"
echo "=========================================================="

# --- 0) Must be an Apple Silicon Mac -----------------------------------------
if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo
  echo "WARNING: This workflow is designed for Apple Silicon Macs (M1-M4)."
  echo "It will not run on Intel Macs or other systems."
  echo
fi

# --- 1) Homebrew --------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  echo
  echo "Homebrew (a free app installer) is not installed yet."
  echo "Please copy-paste this line into Terminal, follow the prompts,"
  echo "then run ./setup.sh again:"
  echo
  echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  echo
  exit 1
fi
echo " [1/3] Homebrew found."

# --- 2) ffmpeg ----------------------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo " [2/3] Installing ffmpeg (this can take a few minutes)..."
  brew install ffmpeg
else
  echo " [2/3] ffmpeg already installed."
fi

# Deno: a small JavaScript runtime that the newest yt-dlp needs to unscramble
# YouTube's download links (without it, some videos fail with HTTP 403).
if ! command -v deno >/dev/null 2>&1; then
  echo " [2/3] Installing deno (needed by yt-dlp for YouTube)..."
  brew install deno
else
  echo " [2/3] deno already installed."
fi

# --- 3) Python virtual environment + mlx-whisper + yt-dlp ---------------------
# Always use Homebrew's modern Python, NOT the Mac's old built-in one (the
# system python is too old for the latest yt-dlp, which keeps up with YouTube).
echo " [3/3] Installing a modern Python..."
brew install python >/dev/null 2>&1 || brew install python
PYTHON="$(brew --prefix)/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"   # fallback, shouldn't normally happen
fi

# Rebuild the environment if it's missing or built on too-old a Python (<3.10).
if [ -d "$VENV" ]; then
  if ! "$VENV/bin/python3" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
    echo " [3/3] Upgrading the Python environment to a newer version..."
    rm -rf "$VENV"
  fi
fi

if [ ! -d "$VENV" ]; then
  echo " [3/3] Creating a private Python environment..."
  "$PYTHON" -m venv "$VENV"
fi

echo " [3/3] Installing mlx-whisper (transcription) and yt-dlp (YouTube downloader)..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet --upgrade mlx-whisper yt-dlp

# Optional: silence/noise skipping (Voice Activity Detection). Bigger download.
# Enable with:  INSTALL_VAD=1 ./setup.sh
if [ "${INSTALL_VAD:-0}" = "1" ]; then
  echo " [3/3] Installing silero-vad (for skipping non-speech audio)..."
  pip install --quiet --upgrade silero-vad
fi

echo
echo "=========================================================="
echo " Tools installed."
echo "=========================================================="

# --- 4) Self-check (also pre-downloads the ~3 GB model) -----------------------
if [ "${SKIP_SELFCHECK:-0}" = "1" ]; then
  echo
  echo " Skipping the self-check (SKIP_SELFCHECK=1)."
  echo " You can run it later with:  ./selfcheck.sh"
else
  echo
  echo " Now running a quick self-check to confirm everything works."
  echo " (This downloads the ~3 GB model one time - please wait.)"
  echo
  bash "$SCRIPT_DIR/selfcheck.sh"
fi

echo
echo "=========================================================="
echo " Setup complete!"
echo
echo " Next steps:"
echo "   1. Put a video file in the 'input' folder."
echo "   2. Run:  ./transcribe.sh"
echo "=========================================================="
