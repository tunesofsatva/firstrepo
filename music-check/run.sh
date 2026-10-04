#!/usr/bin/env bash
#
# Check which Shazam songs are already downloaded on this Mac.
#
# Usage:
#   ./run.sh ~/Downloads/Shazam_Master_Jan-Oct_2026.xlsx
#   ./run.sh ~/Downloads/Shazam_Master_Jan-Oct_2026.xlsx ~/Music "/Volumes/DJ Drive"
#
# With only the Excel file, your whole home folder (except ~/Library) and any
# external drives are scanned. Add folders after the Excel file to scan only
# those. The result is saved next to the Excel as ..._with_downloads.xlsx.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ $# -lt 1 ]; then
  echo "Usage: ./run.sh PATH/TO/Shazam_Master.xlsx [FOLDER ...]"
  exit 1
fi

# Create a private Python environment the first time (Homebrew Python if present).
if [ ! -x "$VENV/bin/python3" ]; then
  PYTHON="python3"
  if command -v brew >/dev/null 2>&1 && [ -x "$(brew --prefix)/bin/python3" ]; then
    PYTHON="$(brew --prefix)/bin/python3"
  fi
  echo "First run: setting up (takes a minute) ..."
  "$PYTHON" -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet openpyxl mutagen rapidfuzz
fi

"$VENV/bin/python3" "$SCRIPT_DIR/check_downloads.py" "$@"
