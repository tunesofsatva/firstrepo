#!/usr/bin/env python3
"""
Detect the parts of an audio file that actually contain speech, using
Silero VAD (Voice Activity Detection). Silence and non-speech noise (e.g.
crowd cheering) between speech regions is left out, so the transcriber can
skip it -- faster, and fewer "stuck repeating" hallucinations.

Prints one speech region per line, as:  <start_seconds> <duration_seconds>

Usage:
    python3 vad_segments.py AUDIO.wav [MAX_SEGMENT_SECONDS]

The input is always a 16 kHz mono 16-bit WAV (produced by the workflow), so
we read it with Python's built-in `wave` module and avoid torchaudio/torchcodec
entirely -- that keeps this working across torch/torchaudio versions.

The printed numbers are in ORIGINAL audio time, so timestamps stay correct
after transcription. Regions longer than MAX_SEGMENT_SECONDS are split (keeps
memory bounded and makes the job resumable).
"""
import sys
import wave

PAD = 0.2        # seconds of breathing room added around each speech region
MERGE_GAP = 1.0  # merge two regions if the gap between them is under this


def refine(regions, max_len, total=None):
    """Pad, merge close regions, and split overly-long ones.

    regions: list of (start, end) in seconds, already sorted by start.
    Returns a list of (start, end) in seconds. Pure function (no audio/ML),
    so it can be unit-tested on its own.
    """
    padded = []
    for s, e in regions:
        s = max(0.0, s - PAD)
        e = e + PAD
        if total is not None:
            e = min(e, total)
        padded.append([s, e])

    merged = []
    for s, e in padded:
        if merged and s - merged[-1][1] <= MERGE_GAP:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    result = []
    for s, e in merged:
        while e - s > max_len:
            result.append((s, s + max_len))
            s += max_len
        if e - s > 0.01:
            result.append((s, e))
    return result


def load_wav_mono(path):
    """Read a 16-bit PCM WAV into a 1-D float torch tensor in [-1, 1]."""
    with wave.open(path, "rb") as w:
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        raw = w.readframes(w.getnframes())

    if sampwidth != 2:
        raise RuntimeError(
            f"expected 16-bit PCM WAV, got sample width {sampwidth} bytes"
        )

    import torch
    # bytearray makes the buffer writable, which torch.frombuffer prefers.
    audio = torch.frombuffer(bytearray(raw), dtype=torch.int16).float() / 32768.0
    if n_channels > 1:
        audio = audio.view(-1, n_channels).mean(dim=1)
    return audio, framerate


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: vad_segments.py AUDIO.wav [MAX_SEGMENT_SECONDS]\n")
        sys.exit(2)
    audio_path = sys.argv[1]
    max_len = float(sys.argv[2]) if len(sys.argv) > 2 else 1800.0

    try:
        import torch  # noqa: F401  (needed by load_wav_mono and silero)
        from silero_vad import load_silero_vad, get_speech_timestamps
    except ImportError:
        sys.stderr.write(
            "ERROR: silence-skipping needs the 'silero-vad' tool, which isn't "
            "installed.\nRun this once:  INSTALL_VAD=1 ./setup.sh\n"
        )
        sys.exit(3)

    audio, sr = load_wav_mono(audio_path)
    total = audio.shape[0] / float(sr)

    model = load_silero_vad()
    stamps = get_speech_timestamps(
        audio, model, sampling_rate=sr, return_seconds=True
    )
    regions = [(float(t["start"]), float(t["end"])) for t in stamps]
    for s, e in refine(regions, max_len, total):
        sys.stdout.write(f"{s:.3f} {e - s:.3f}\n")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        out = refine([(1, 2), (2.5, 3), (10, 2000)], max_len=600, total=2100)
        for s, e in out:
            print(f"{s:.3f} {e:.3f}")
        sys.exit(0)
    main()
