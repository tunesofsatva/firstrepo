# Local Video Transcription (for Apple Silicon Macs)

Turn long videos into **text transcripts** and **subtitles**, entirely on your
own MacBook. No subscriptions, no upload limits, no monthly fees. Works fully
offline after the one-time setup.

This is built and tuned for **Apple Silicon (M1–M4)** Macs and uses
**MLX-Whisper**, Apple's own GPU-accelerated speech-to-text engine — the
fastest accurate option for your M4.

It handles very long videos (3.5–7 hours) automatically. You never split
anything by hand.

---

## What you get for each video

- `name.txt` — the full transcript as plain text
- `name.srt` — subtitles with timestamps (great for jumping to a moment)
- `name.md` — a Markdown transcript with timestamps (nice for analysing in
  Claude — you can ask it about a specific moment)

All three land in the `output` folder. Any of them can be uploaded to Claude;
the `.md` or `.txt` are the easiest to work with.

---

## One-time setup (do this once)

1. Open the **Terminal** app (press `Cmd + Space`, type "Terminal", press Enter).
2. Go into this folder. The easy way: type `cd ` (with a space), then drag the
   `transcribe` folder onto the Terminal window, then press Enter.
3. Run the setup:

   ```
   ./setup.sh
   ```

   If it says Homebrew is missing, it will print one line for you to copy-paste
   first; do that, then run `./setup.sh` again.

That's it. Setup installs everything needed, then automatically runs a quick
**self-check**: it speaks a short test sentence, transcribes it, and confirms
the words come back. When you see `RESULT: PASSED`, your Mac is ready.

> The self-check downloads the language model (~3 GB) one time, so your first
> real video runs without waiting. After that everything works offline.

You can re-run the self-check any time:

```
./selfcheck.sh
```

---

## Transcribing YouTube videos

This tool transcribes **files**, so YouTube videos are downloaded first (as
audio only — smaller and faster, and audio is all we need for a transcript).

1. Open the file **`youtube-urls.txt`**, paste your links (one per line), save.
   A playlist link works too — every video in it is downloaded.
2. Download them:

   ```
   ./download.sh
   ```

   (Or skip the file and pass a link directly:
   `./download.sh "https://youtu.be/your-link"`)
3. Now transcribe what was downloaded:

   ```
   ./transcribe.sh
   ```

4. **Collect** your results from the `output` folder: a `.txt` and `.srt` per
   video.

Both `download.sh` and `transcribe.sh` remember what they've finished, so if
something is interrupted you can just run them again and they pick up where
they left off.

> Only download content you have the right to use. yt-dlp is a standard
> open-source tool; downloads happen entirely on your Mac.

## Transcribing your own video files

1. **Drop** video files (or audio files) into the `input` folder.
   (You can drop several at once.)
2. In Terminal, in this folder, **run one command:**

   ```
   ./transcribe.sh
   ```

3. **Collect** your results from the `output` folder:
   `yourvideo.txt` and `yourvideo.srt`.

While it runs, it prints progress like `transcribing chunk 3 of 14`. A long
video takes a while — you can leave it running.

---

## Good to know

- **Long videos are automatic.** Behind the scenes the audio is split into
  30-minute chunks, each is transcribed, then stitched back together with
  correct timestamps. You do nothing.
- **Safe to stop and restart.** If you close the Terminal or your Mac sleeps,
  just run `./transcribe.sh` again — it resumes where it left off and skips
  videos that are already finished.
- **Re-doing a video:** delete its `.txt` and `.srt` from `output`, then run
  `./transcribe.sh` again.
- **Feeding transcripts to Claude later:** the `.txt` files are plain text and
  ready to paste or upload. The `.srt` files are best when you want Claude to
  reference specific timestamps.

---

## Optional settings (advanced — you can ignore these)

Run with a setting in front of the command. Examples:

- Faster, still very accurate (good for many hours of content):

  ```
  MODEL=mlx-community/whisper-large-v3-turbo ./transcribe.sh
  ```

- Auto-detect the language instead of assuming English:

  ```
  LANGUAGE=auto ./transcribe.sh
  ```

- Change the internal chunk size to 20 minutes:

  ```
  CHUNK_MINUTES=20 ./transcribe.sh
  ```

| Setting | Default | What it does |
|---|---|---|
| `MODEL` | `mlx-community/whisper-large-v3-mlx` | Accuracy vs speed. `...turbo` is faster. |
| `LANGUAGE` | `en` | Spoken language. `auto` = detect automatically. |
| `CHUNK_MINUTES` | `30` | Internal chunk length. `0` = no chunking. |
| `CONDITION_ON_PREVIOUS` | `False` | Keep `False` to avoid repeated-text loops during crowd noise/silence (common in sports & events). `True` = Whisper's default. |

---

## Troubleshooting

- **"ffmpeg is not installed" / "mlx_whisper is not installed"** → run
  `./setup.sh` first.
- **"command not found: ./setup.sh"** → make sure you `cd`'d into the
  `transcribe` folder (see setup step 2).
- **Permission denied** → run `chmod +x setup.sh transcribe.sh` once, then try
  again.
- **It's slow** → that's normal for multi-hour videos. Try the `turbo` model
  (see above) for a big speed-up with a small accuracy trade-off.

---

## Why MLX-Whisper (and not Faster-Whisper)?

Faster-Whisper is excellent on NVIDIA GPUs, but its engine (CTranslate2) has
**no Metal GPU support on Macs** — on your M4 it would run on the CPU only and
leave the GPU idle. **MLX-Whisper** is Apple's framework and runs on the M4
**GPU**, so it's both faster and a more natural fit for your machine, while
using the same high-accuracy Whisper `large-v3` model.
