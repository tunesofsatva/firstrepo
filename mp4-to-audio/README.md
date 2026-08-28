# MP4 / WAV → audio converter

Recursively converts every `.mp4` and `.wav` under a folder (any subfolder
depth) into a high-quality `.m4a` placed **right next to the original**. By
default **nothing is deleted** — you verify the results (e.g. Traktor cue
points) first, then delete the originals in a separate, safe step.

## Codec choice (goal: highest quality, least loss)

| Source | What happens | Loss |
| --- | --- | --- |
| `.mp4` with AAC/ALAC audio | audio **copied out**, no re-encode | none |
| `.wav` (PCM), `.flac`, other lossless | encoded to **ALAC** (lossless) in `.m4a` | none |
| other lossy (mp3, ac3, opus, …) | re-encoded to **AAC 256k** | minimal |

`.m4a` beats `.mp3`: it holds both AAC and lossless ALAC, and is a stronger,
less-limited format. `--mp3` forces lossy MP3 only if you specifically want it.

WAV is already lossless, so it goes to **ALAC** (lossless) — converting it to a
lossy format would *lose* quality, so the script doesn't.

## Traktor cue points / metadata — read this

Standard tags (title, artist, genre, bpm, comment) are carried over. But Traktor
**cue points and beatgrids** usually live in Traktor's `collection.nml`, not in
the file; any embedded copy is a proprietary tag that may not survive a format
change. So there is **no guarantee** cues survive conversion. Safe workflow:

1. **Back up `collection.nml`** (in `~/Documents/Native Instruments/Traktor…/`).
2. Convert — originals are **kept** by default.
3. Import a new `.m4a` into Traktor and **check one track**: are the cues/grid
   there?
4. If yes → delete originals (step below). If no → keep originals; the cues were
   database-only and would be lost.

## Install ffmpeg (one time)

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install ffmpeg`

## Use

```bash
# 1) Preview (changes nothing):
./convert-mp4-to-audio.sh --dry-run "/path/to/your/music folder"

# 2) Convert, KEEPING every original (safe default):
./convert-mp4-to-audio.sh "/path/to/your/music folder"

# 3) After you've verified cues/metadata in Traktor, delete the originals
#    (only deletes a .mp4/.wav that has a valid .m4a sibling next to it):
./convert-mp4-to-audio.sh --delete-verified "/path/to/your/music folder"
```

Other options: `--delete` (convert and delete in one shot), `--mp3` (lossy MP3
output), `-h` (help).

## Safety guarantees

- Deep subfolders are handled; each output stays in the source's own folder.
- An original is deleted **only** when a non-empty, ffprobe-valid `.m4a` sibling
  exists. A failed/partial conversion never triggers a delete.
- Existing output files are never overwritten. Spaces/unicode in names are safe.
