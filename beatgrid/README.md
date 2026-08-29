# beatgrid — exact BPM & beat-grid analysis (Traktor, on Apple Silicon Macs)

You know the problem: a track *says* 128 BPM, so you set Traktor's grid to 128 —
and a few bars in it slides off the beat. It "goes forward, then backward." You
try 128.5, worse. You guess 126, suddenly it locks. Ten minutes of
trial-and-error **per track**.

> **Traktor note:** Traktor uses **one fixed beatgrid per track** — a single
> BPM plus a single grid marker (the anchor). It can't re-anchor the grid
> mid-song the way Serato/Rekordbox can. So the two fixes here are: the
> **exact decimal BPM** for steady tracks (most of them), and **warping** for
> tracks that genuinely drift. (Traktor hotcues are handy markers but do *not*
> correct the grid — see below.)

---

## ⭐ The simple way — start here (two commands)

Everything lands in **this `beatgrid` folder** or **right next to your own
music**. Nothing gets scattered, nothing of yours is modified.

**One-time install:** `./setup.sh`

**Step 1 — see what's wrong (changes nothing):**

```
COLLECTION="$HOME/Documents/Native Instruments/Traktor 3.11.1/collection.nml" \
  ./1-scan.sh "/Users/you/Music/DJ"
```

This writes **`beatgrid-report.xlsx`** in this folder. Open it — every track is
labelled **GOOD**, **WRONG NUMBER**, or **DRIFTS**, with its current BPM, its
correct BPM, your cue-point count, and its full path. The counts are printed too.
(You can point it at several folders at once, and leave off `COLLECTION=` if you
just want the correct BPMs without comparing to Traktor.)

**Step 2 — fix them (preview first, then APPLY):**

```
# preview — writes nothing:
COLLECTION="…/collection.nml" ./2-fix.sh "/Users/you/Music/DJ"

# quit Traktor, then really do it:
COLLECTION="…/collection.nml" ./2-fix.sh "/Users/you/Music/DJ" APPLY
```

By default it **only fixes BPM + grid numbers** inside Traktor — **no new files,
no quality loss, and every rating / comment / cue point kept exactly as-is**.
This handles both WRONG NUMBER tracks and drifting ones (a drifting track gets
its best single BPM; a small wander may remain, but nothing is re-encoded).

Only add **`WARP`** if you want drifting tracks re-timed into brand-new
straightened copies:

```
./2-fix.sh "/Users/you/Music/DJ" APPLY WARP
```

Warping re-encodes the audio and costs ~2–3 dB of loudness, so use it sparingly
on genuinely wobbly tracks. It writes `… (fixed 123).m4a` next to each original
(tags, artwork, cue points carried) plus a delete-old script.

APPLY writes a **new** `collection.beatgrid.nml` next to your real one (yours is
never overwritten). To load the fixes: quit Traktor, back up your
`collection.nml`, then replace it with `collection.beatgrid.nml`. **Your
ratings, comments and cues live inside Traktor** — so they come back when you
load this file, not by re-importing a track.

**Step 3 — listen.** Open `beatgrid-report.xlsx` and play the original vs. the
fixed copy from the paths shown.

**Step 4 — delete the old ones.** When you're happy, double-click
**`delete-old-versions.command`** (in this folder). It moves the replaced
originals to the **Trash** (recoverable). One good track remains.

> Safety: your original audio files are never modified, your real
> `collection.nml` is never overwritten, and nothing is deleted unless *you* run
> the delete file yourself.

Everything below is the detailed reference — you can ignore it unless you want
the individual commands.

---

`beatgrid` measures where the beats **actually** are and tells you the answer
instead of making you guess:

- the **exact BPM** to type in (to 3 decimals, e.g. `127.960`, not "128-ish"),
- **where to anchor** the grid (the first downbeat, to the millisecond),
- whether the track is **steady** (one BPM fixes it forever) or **drifting**
  (no single BPM can ever hold),
- for drifting tracks, **reset cue points** — a time + a fresh BPM for each
  stretch that holds steady before it drifts again,
- and, if you want, a **warped lossless copy** whose beats are perfectly even
  so any constant BPM lines up end-to-end.

It runs entirely on your Mac. Nothing is uploaded. Your original files are
never modified.

---

## Why your grids drift (the two real causes)

DJ software draws evenly spaced grid lines and assumes **one constant BPM**.
Two things break that:

1. **The true tempo isn't a round number.** A track mastered from a DAW is
   dead steady but at `127.96`, not `128.000`. Set `128` and the grid gains
   ~0.3 ms per beat — after ~30 beats (about 14 s) it's visibly off, and it
   keeps sliding. This is *most* of your tracks, and the fix is simply the
   precise decimal BPM. `beatgrid` gives it to you.

2. **The tempo genuinely drifts.** Live drummer, old record, no click track.
   The BPM wanders (say 125–128 across the song). No single number works —
   here you either drop **reset cue points** or **warp** the file.

`beatgrid` tells you which case you're in for every track.

---

## One-time setup (do this once)

1. Open the **Terminal** app (`Cmd + Space`, type "Terminal", Enter).
2. Go into this folder: type `cd ` (with a space), drag the `beatgrid` folder
   onto the Terminal window, press Enter.
3. Run:

   ```
   ./setup.sh
   ```

   If it says Homebrew is missing, it prints one line to copy-paste first; do
   that, then run `./setup.sh` again.

Setup installs `ffmpeg` (reads your audio), `rubberband` (for warping), and a
private Python environment, then runs a self-check on a test track with a known
BPM. When you see `RESULT: PASSED`, you're ready.

---

## Option 1 — the exact BPM (fixes most tracks)

1. Drop one or more tracks (MP3, M4A, WAV, AIFF, FLAC…) into the `input` folder.
2. Run:

   ```
   ./analyze.sh
   ```

You get, per track:

```
  Track      : Midnight Drive.mp3
  Length     : 6:12.400  (742 beats detected)
  BPM to set : 127.960   (nearest whole number: 128)
  Anchor grid: first downbeat at 0:00.512  (0.512 s)
  Verdict    : CONSTANT tempo. Set BPM = 127.960, anchor the grid on the
               first downbeat, and it lines up for the whole track.
```

In Traktor: open the **Grid** panel, type the BPM as **127.960** (Traktor takes
2 decimals), and move the **grid marker** onto the reported downbeat. It holds
for the whole song. No more nudging.

A copy of each report is saved in `output/` as `.txt` (to read) and `.json`
(for later automation).

---

## Option 2 — drifting tracks: warp them (and the section-tempo reference)

When a track genuinely drifts, `analyze.sh` says so:

```
  Verdict    : DRIFTING tempo (varies 125.1-127.9 BPM; the grid wanders up
               to 294 ms off the beat). No single BPM can hold. Traktor uses
               ONE fixed grid per track, so the clean fix is to WARP it:
                   ./warp.sh "Live Set.wav" 126
               then set BPM 126 and one grid marker on beat 1.
               Section tempos below are for reference / manual hotcues
               (Traktor hotcues do NOT re-grid the track):
                   0:00.221   -> 125.917 BPM
                   0:37.454   -> 126.932 BPM
                   1:11.019   -> 126.266 BPM
                   ...
```

**Why warp, not cues, in Traktor.** In Serato or Rekordbox you'd drop several
grid markers to re-anchor the grid at each of those times. Traktor doesn't
support multiple grid markers — one fixed grid per track — so cues there are
just trigger points and won't straighten a drifting track. Warping (Option 3)
re-times the audio so the beat *is* even, which Traktor's single grid can then
hold. The section tempos are still worth knowing if you prefer to beatmatch
those stretches by ear.

> **Tune the sensitivity:** `DRIFT_MS` sets how far (in milliseconds) the grid
> may wander before a track counts as drifting. Default is 25 ms. Stricter:
> `DRIFT_MS=15 ./analyze.sh`. Looser: `DRIFT_MS=40`.

---

## Option 3 — warp to a perfectly even grid (lossless)

Don't want to fuss with cues? Warp the audio so its beats become perfectly
even, then one constant BPM lines up for the whole track:

```
./warp.sh "input/Live Set.wav" 128
```

This writes a **new lossless WAV** to `output/` (your original is untouched).
Import it, set the BPM to 128, anchor beat 1, done. If you leave off the number
it warps to the BPM `beatgrid` detects.

> Warping re-times the audio (high-quality `rubberband` engine). It's the
> hands-off fix for drifting tracks. For steady tracks you don't need it —
> Option 1's decimal BPM is cleaner because it doesn't touch the audio at all.

---

## Option 4 — scan your whole library

Point it at a folder and it checks every track underneath, flags the ones that
are out of sync, and writes a spreadsheet you can sort:

```
./scan.sh ~/Music/DJ
```

```
  OK        127.960 BPM  drift<=     4ms   Midnight Drive.mp3
  >> DRIFT  126.485 BPM  drift<=   294ms   Live Set.wav
  OK        124.000 BPM  drift<=     6ms   Deep Cut.m4a
  ...
  Done. 312 analysed, 27 drifting / out of sync.
  Full table: output/library-scan.csv
```

Open `output/library-scan.csv` in Numbers/Excel, sort by `drift_max_ms`, and
you've got a worklist: the `>> DRIFT` tracks are the ones worth warping or
cueing; everything else just needs its precise decimal BPM.

---

## Option 5 — fix your whole Traktor library automatically

Instead of retyping BPMs track by track, `beatgrid` can read your Traktor
`collection.nml` and write the exact BPM + a grid marker on the true downbeat
for every track it can analyse. Drifting tracks also get a warped copy in
`output/`.

**This edits Traktor's collection, so it is deliberately careful:**
it dry-runs by default, writes to a *new* `collection.beatgrid.nml` (never your
original) unless you insist, only ever changes the BPM and one grid marker, and
never touches your hotcues or loops.

Your collection file lives at roughly:
`~/Documents/Native Instruments/Traktor 3.x.x/collection.nml`

Do it in three steps:

```
# 1) Confirm your track paths decode correctly (nothing is analysed or written)
./sync-traktor.sh CHECK "~/Documents/Native Instruments/Traktor 3.x.x/collection.nml"

# 2) Dry run on a handful of tracks - see the changes, write nothing
./sync-traktor.sh DRY   "~/.../collection.nml" --limit 5

# 3) Write to a NEW file (collection.beatgrid.nml, next to your original)
./sync-traktor.sh APPLY "~/.../collection.nml"
```

> **Before APPLY: quit Traktor** (it rewrites `collection.nml` on exit and would
> undo the changes). After it writes `collection.beatgrid.nml`, back up your
> real `collection.nml`, then replace it with the new file (or import it).

Useful flags after the path: `--limit 20` (first 20 tracks), `--only-under
~/Music/DJ` (just that folder), `--drift skip` (don't render warped copies).

---

## Cheat sheet

| I want… | Command |
|---|---|
| The exact BPM for tracks in `input/` | `./analyze.sh` |
| The exact BPM for one file | `./analyze.sh "path/to/track.mp3"` |
| A warped, perfectly-even copy | `./warp.sh "path/to/track.mp3" 128` |
| To scan my whole library | `./scan.sh ~/Music/DJ` |
| To fix my whole Traktor collection | `./sync-traktor.sh DRY "~/.../collection.nml"` |
| Stricter drift detection | `DRIFT_MS=15 ./analyze.sh` |
| Allow very slow/fast tempos | `BPM_MIN=60 BPM_MAX=200 ./analyze.sh` |

---

## Good to know / troubleshooting

- **Accuracy.** Over a full track (hundreds of beats) the BPM is pinned to a
  few thousandths — in the self-check it recovers `127.960` from `127.960`.
- **Half/double time.** If a track reports half or double what you expect (64
  vs 128), widen the range: `BPM_MIN=60 BPM_MAX=200 ./analyze.sh`. It searches
  octaves and keeps the musical one.
- **"ffmpeg is not installed" / "run setup"** → run `./setup.sh` first.
- **"command not found: ./analyze.sh"** → make sure you `cd`'d into this
  `beatgrid` folder.
- **Permission denied** → run `chmod +x *.sh` once, then try again.
- **Formats.** MP3, M4A/AAC, WAV, AIFF, FLAC, OGG, and video files (it reads
  the audio). Same lossless-friendly toolchain as the transcribe workflow.
- **Nothing is uploaded** and your originals are never changed — `warp.sh`
  only ever writes new files into `output/`.
