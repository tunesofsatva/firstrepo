# beatgrid — exact BPM & beat-grid analysis (for Apple Silicon Macs)

You know the problem: a track *says* 128 BPM, so you set the grid to 128 — and
a few bars in it slides off the beat. It "goes forward, then backward." You try
128.5, worse. You guess 126, suddenly it locks. Ten minutes of trial-and-error
**per track**.

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

In your DJ software: set the BPM to **127.960** (Rekordbox/Serato/Traktor all
accept decimals), drop the first grid line on the reported downbeat, and it
holds for the whole song. No more nudging.

A copy of each report is saved in `output/` as `.txt` (to read) and `.json`
(for later automation).

---

## Option 2 — reset cue points (for drifting tracks)

When a track genuinely drifts, `analyze.sh` says so and hands you cue points:

```
  Verdict    : DRIFTING tempo (varies 125.1-127.9 BPM; the grid wanders up
               to 294 ms off the beat). No single BPM can hold. Two fixes:
               (a) warp it:  ./warp.sh "Live Set.wav" 126
               (b) or drop these reset cue points (time -> local BPM):
                   CUE  1  0:00.221   -> 125.917 BPM
                   CUE  2  0:04.064   -> 127.589 BPM
                   CUE  3  0:37.454   -> 126.932 BPM
                   CUE  4  1:11.019   -> 126.266 BPM
                   ...
```

Each cue is a point where the beat has drifted far enough that you should
**re-anchor** the grid and switch to the new local BPM shown. Place a cue/memory
point at each time and re-grid from there — exactly the "resetting cue point"
idea you described, computed for you.

> **Tune the sensitivity:** `DRIFT_MS` sets how far (in milliseconds) the grid
> may wander before a track counts as drifting / a new cue is suggested.
> Default is 25 ms. Stricter: `DRIFT_MS=15 ./analyze.sh`. Looser: `DRIFT_MS=40`.

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

## Cheat sheet

| I want… | Command |
|---|---|
| The exact BPM for tracks in `input/` | `./analyze.sh` |
| The exact BPM for one file | `./analyze.sh "path/to/track.mp3"` |
| A warped, perfectly-even copy | `./warp.sh "path/to/track.mp3" 128` |
| To scan my whole library | `./scan.sh ~/Music/DJ` |
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
