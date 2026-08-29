#!/usr/bin/env bash
#
# One-time setup for the beatgrid workflow (Apple Silicon Macs).
#
# It installs:
#   * ffmpeg      - reads your MP3/M4A/WAV files (and video) and decodes audio
#   * rubberband  - (optional) high-quality time-stretch, used by ./warp.sh
#   * a private Python environment with the audio-analysis libraries
#
# Run it once:
#   ./setup.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

echo "=========================================================="
echo " Setting up beatgrid (exact BPM + beat-grid analysis)"
echo "=========================================================="

# --- 0) Apple Silicon check ---------------------------------------------------
if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo
  echo "NOTE: tuned for Apple Silicon Macs (M1-M4). It should still work"
  echo "elsewhere as long as ffmpeg and Python 3.10+ are available."
  echo
fi

# --- 1) Homebrew --------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  echo
  echo "Homebrew (a free app installer) is not installed yet."
  echo "Copy-paste this line into Terminal, follow the prompts, then run"
  echo "./setup.sh again:"
  echo
  echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  echo
  exit 1
fi
echo " [1/3] Homebrew found."

# --- 2) ffmpeg (+ optional rubberband) ---------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo " [2/3] Installing ffmpeg (this can take a few minutes)..."
  brew install ffmpeg
else
  echo " [2/3] ffmpeg already installed."
fi

# rubberband is only needed for ./warp.sh. Install it too (it's small) unless
# you set SKIP_RUBBERBAND=1.
if [ "${SKIP_RUBBERBAND:-0}" != "1" ]; then
  if ! command -v rubberband >/dev/null 2>&1; then
    echo " [2/3] Installing rubberband (for ./warp.sh)..."
    brew install rubberband || echo "   (rubberband failed - warp.sh will be unavailable, everything else works)"
  else
    echo " [2/3] rubberband already installed."
  fi
fi

# --- 3) Python environment ----------------------------------------------------
echo " [3/3] Installing a modern Python..."
brew install python >/dev/null 2>&1 || brew install python
PYTHON="$(brew --prefix)/bin/python3"
[ -x "$PYTHON" ] || PYTHON="python3"

if [ -d "$VENV" ]; then
  if ! "$VENV/bin/python3" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
    echo " [3/3] Upgrading the Python environment..."
    rm -rf "$VENV"
  fi
fi
[ -d "$VENV" ] || "$PYTHON" -m venv "$VENV"

echo " [3/3] Installing analysis libraries (numpy, scipy, soundfile, librosa)..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet --upgrade numpy scipy soundfile librosa

echo
echo "=========================================================="
echo " Tools installed."
echo "=========================================================="

if [ "${SKIP_SELFCHECK:-0}" = "1" ]; then
  echo " Skipping the self-check (SKIP_SELFCHECK=1)."
else
  echo
  echo " Running a quick self-check (builds a test track with a known BPM"
  echo " and confirms beatgrid recovers it)..."
  echo
  bash "$SCRIPT_DIR/selfcheck.sh"
fi

echo
echo "=========================================================="
echo " Setup complete!"
echo
echo " Next steps:"
echo "   1. Put an MP3/M4A/WAV in the 'input' folder."
echo "   2. Run:  ./analyze.sh"
echo "=========================================================="
