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

# --- 3) Python virtual environment + mlx-whisper ------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo " [3/3] Installing Python..."
  brew install python
fi

if [ ! -d "$VENV" ]; then
  echo " [3/3] Creating a private Python environment..."
  python3 -m venv "$VENV"
fi

echo " [3/3] Installing mlx-whisper (Apple's transcription engine)..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet --upgrade mlx-whisper

echo
echo "=========================================================="
echo " Setup complete!"
echo
echo " Next steps:"
echo "   1. Put a video file in the 'input' folder."
echo "   2. Run:  ./transcribe.sh"
echo
echo " The first run will download the transcription model"
echo " (about 3 GB) one time. After that it works offline."
echo "=========================================================="
