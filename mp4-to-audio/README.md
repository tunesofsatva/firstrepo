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

## Traktor fields — what carries over

Which Traktor columns survive conversion depends on whether Traktor wrote them
into the FILE (many fields live only in `collection.nml`) and whether ffmpeg
re-writes them. Observed behavior:

| Traktor field | Carries over? |
| --- | --- |
| Title, Artist, Genre, Comment (1) | ✅ reliably |
| BPM, Key | ⚠️ at risk (Traktor regenerates on re-analysis) |
| Rating, Comment 2 | ❌ likely lost (non-standard / Traktor-only fields) |
| Cue points, beatgrid | ❌ no guarantee (usually database-only) |

The fields most likely NOT to carry into the file (Rating, Comment 2, cues) are
exactly the ones Traktor keeps in `collection.nml`. So if you **back up
`collection.nml`** and **keep the originals** (the default), nothing is truly
lost — worst case you re-link/re-analyze the new `.m4a` in Traktor.

**Verify on YOUR files before deleting** with the included inspector — it shows
every embedded tag, before vs after:

```bash
./inspect-tags.sh "/path/to/one/folder"      # before/after per track
./inspect-tags.sh "/path/to/a/file.m4a"      # single file
```

Install `exiftool` (`brew install exiftool`) for the fullest view — it reads
Traktor's proprietary atoms that ffprobe hides.

Safe workflow:
1. **Back up `collection.nml`** (`~/Documents/Native Instruments/Traktor…/`).
2. Convert — originals are **kept** by default.
3. Run `./inspect-tags.sh` on that folder and/or check one track in Traktor.
4. Happy? → `--delete-verified`. Not happy? → keep originals; data stays safe in
   `collection.nml` + the untouched originals.

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
