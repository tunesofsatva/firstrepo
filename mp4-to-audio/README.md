# MP4 → audio converter

Recursively converts every `.mp4` under a folder into a high-quality audio file
placed **right next to the original** (same subfolder), then deletes the
original `.mp4` **after** verifying the new file — and prints a proof report.

## Why M4A, not MP3?

Your `.mp4` files almost always already contain **AAC** audio. An `.m4a` file is
the same MPEG-4/AAC container, so the audio is copied out with **no re-encoding
= zero quality loss** (a "remux"). MP3 would force a lossy re-encode, and AAC is
a stronger codec than MP3 anyway. So **`.m4a` is both higher quality and less
limited** — it is the default. If a file's audio isn't already AAC/ALAC, it's
re-encoded to AAC at 256 kbps (transparent). Use `--mp3` only if you truly need
MP3.

## Install ffmpeg (one time)

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install ffmpeg`
- Windows: `winget install Gyan.FFmpeg`

## Use

```bash
# Preview first (changes nothing):
./convert-mp4-to-audio.sh --dry-run "/path/to/your/music folder"

# Do it for real (converts, then deletes the .mp4 originals):
./convert-mp4-to-audio.sh "/path/to/your/music folder"
```

Options: `--dry-run` (preview), `--keep` (convert but keep the `.mp4`),
`--mp3` (produce `.mp3` instead of `.m4a`), `-h` (help).

## Safety

An original `.mp4` is deleted **only after** the new audio file exists, is
non-empty, and `ffprobe` confirms it holds a valid audio stream. Existing output
files are never overwritten. Filenames with spaces/unicode and arbitrarily deep
subfolders are handled.
