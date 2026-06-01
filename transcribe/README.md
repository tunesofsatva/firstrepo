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

Both land in the `output` folder.

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

That's it. Setup installs everything needed.

> The **first** time you transcribe, it downloads the language model (~3 GB)
> one time. After that it runs offline.

---

## Everyday use (3 steps)

1. **Drop** a video file into the `input` folder.
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
