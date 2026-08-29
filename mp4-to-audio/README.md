# MP4 / WAV → audio converter

Recursively converts every `.mp4` and `.wav` under a folder (any subfolder
depth) into a high-quality `.m4a` placed **right next to the original**. By
default **nothing is deleted** — you verify the results (e.g. Traktor cue
points) first, then delete the originals in a separate, safe step.

## ✅ Quick start (do this in order)

**One-time setup** (Mac):
- [ ] `brew install ffmpeg exiftool`
- [ ] `pip3 install mutagen`
- [ ] Back up `collection.nml` (in `~/Documents/Native Instruments/Traktor …/`) —
      quit Traktor first so it saves, then copy the file somewhere safe.

**Each folder you want to convert:**
- [ ] 1. **Trial run first** — pick ONE small folder with a few cued tracks.
- [ ] 2. **Preview** (changes nothing):
      `./run-all.sh --collection "<collection.nml>" --dry-run "<folder>"`
- [ ] 3. **Run it** (convert + relink cues/grid + stamp tags; keeps originals):
      `./run-all.sh --collection "<collection.nml>" --stamp "<folder>"`
- [ ] 4. **Verify in Traktor:** quit Traktor → back up live `collection.nml` →
      rename `collection_RELINKED.nml` to `collection.nml` → open Traktor →
      load one `.m4a` → confirm cues/loops/grid are there.
- [ ] 5. **Spot-check tags** (optional): `./inspect-tags.sh "<folder>"`
- [ ] 6. **Delete originals** once happy:
      `./convert-mp4-to-audio.sh --delete-verified "<folder>"`
- [ ] 7. Happy with the trial? Repeat 2–6 for the rest.

> Tip: drag a folder (or the `collection.nml` file) from Finder onto the Terminal
> to paste its full path. Nothing is deleted until step 6, and your original
> `collection.nml` is never modified (relink writes a new file).

**The tools:** `run-all.sh` (pipeline) · `convert-mp4-to-audio.sh` (convert +
safe delete) · `relink-collection.py` (cues/loops/grid → `.m4a`, for Traktor) ·
`stamp-from-collection.py` (tags → `.m4a`, for other apps) · `inspect-tags.sh`
(verify embedded tags).

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

## One command for everything (run-all.sh)

Chains the safe steps for a folder — **convert → relink → (optional) stamp** —
and deletes nothing:

```bash
# convert + relink cues/grid (+ stamp tags with --stamp):
./run-all.sh --collection "/path/collection.nml" --stamp "/music/folder"

# convert only (no Traktor collection):
./run-all.sh "/music/folder"
```

Add `--dry-run` to preview the whole chain. After you verify in Traktor, delete
originals with `./convert-mp4-to-audio.sh --delete-verified "/music/folder"`.

## Stamp Traktor metadata into the converted files

`stamp-from-collection.py` writes the fields you curated in Traktor —
**Rating, Comment 1, Comment 2, Mix, Genre, Key, BPM, Artist, Album, Remixer,
Label** — from `collection.nml` directly into your converted `.m4a` files. This
is the reliable way to make that data permanent in the file, because it doesn't
depend on whether Traktor ever wrote tags to the originals.

It matches each `.m4a` to its Traktor entry by `<parent folder>/<filename stem>`
(falling back to the filename stem), only **adds** the fields above (never blanks
others), and writes a `stamp-log.csv` record. Star rating comes from Traktor's
`RANKING` (÷51 = 0–5); Comment 2 comes from Traktor's oddly-named `RATING`
attribute. Cue points/beatgrids are **not** written (Traktor keeps those in
`collection.nml` only — that file remains your cue backup).

```bash
pip3 install mutagen        # one time

# preview matches (writes nothing):
python3 stamp-from-collection.py --collection "/path/collection.nml" --dry-run "/music/folder"
# stamp for real:
python3 stamp-from-collection.py --collection "/path/collection.nml" "/music/folder"
```

Comment 2 and Rating are stored as freeform tags under `com.apple.iTunes:`
(`COMMENT2`, `RATING_STARS`, `MIX`, `INITIALKEY`, `REMIXER`, `LABEL`), readable by
exiftool, mutagen, MediaMonkey, etc. Verify with `./inspect-tags.sh`.

## Carry cues, loops & beatgrid to the new files (relink-collection.py)

Traktor stores your cue points, loops and beatgrid inside each track's entry in
`collection.nml`, linked to the file by name. Converting `song.wav` -> `song.m4a`
leaves the entry pointing at the old file. `relink-collection.py` **repoints the
entry to the new `.m4a`** — so the *same* entry (with all its cues, loops, grid,
BPM, key, rating, comments, color, play count) now belongs to the `.m4a`. No
manual re-cueing.

It writes a **new** collection file and never modifies your original.

```bash
# preview (writes nothing):
python3 relink-collection.py --collection "/path/collection.nml" --dry-run "/music/folder"
# produce collection_RELINKED.nml:
python3 relink-collection.py --collection "/path/collection.nml" "/music/folder"
```

Then, in Traktor: **quit Traktor**, back up your live `collection.nml`, replace it
with the RELINKED file (rename to `collection.nml`), reopen, and load one `.m4a`
to confirm cues/loops/grid are all present. Test on a copy first.

Cue alignment is exact for lossless conversions (WAV→ALAC, MP4 AAC copy) because
the audio timing is unchanged; lossy re-encodes can shift a few ms. Only entries
whose file is a source type (`.wav .mp4 .aif .aiff .flac .mov .m4v .avi`) are
repointed. `relink` (for Traktor) and `stamp` (for file tags, used outside
Traktor) are complementary — use either or both.

## Install ffmpeg (one time)

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install ffmpeg`

## Use

```bash
# 1) Preview (changes nothing):
./convert-mp4-to-audio.sh --dry-run "/path/to/your/music folder"

# 2) Convert, KEEPING every original (safe default):
./convert-mp4-to-audio.sh "/path/to/your/music folder"

# 3) Stamp your Traktor metadata (rating, comments, etc.) into the new .m4a files:
python3 stamp-from-collection.py --collection "/path/collection.nml" "/path/to/your/music folder"

# 4) After you've verified in Traktor, delete the originals
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
