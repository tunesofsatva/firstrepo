#!/usr/bin/env python3
"""
Detect the parts of an audio file that actually contain speech, using
Silero VAD (Voice Activity Detection). Silence and non-speech noise (e.g.
crowd cheering) between speech regions is left out, so the transcriber can
skip it -- faster, and fewer "stuck repeating" hallucinations.

Prints one speech region per line, as:  <start_seconds> <duration_seconds>

Usage:
    python3 vad_segments.py AUDIO.wav [MAX_SEGMENT_SECONDS]

The numbers are in ORIGINAL audio time, so timestamps stay correct after
transcription. Regions longer than MAX_SEGMENT_SECONDS are split (keeps
memory bounded and makes the job resumable).
"""
import sys

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


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: vad_segments.py AUDIO.wav [MAX_SEGMENT_SECONDS]\n")
        sys.exit(2)
    audio = sys.argv[1]
    max_len = float(sys.argv[2]) if len(sys.argv) > 2 else 1800.0

    try:
        from silero_vad import (
            load_silero_vad,
            read_audio,
            get_speech_timestamps,
        )
    except ImportError:
        sys.stderr.write(
            "ERROR: silence-skipping needs the 'silero-vad' tool, which isn't "
            "installed.\nRun this once:  INSTALL_VAD=1 ./setup.sh\n"
        )
        sys.exit(3)

    model = load_silero_vad()
    wav = read_audio(audio, sampling_rate=16000)
    total = len(wav) / 16000.0
    stamps = get_speech_timestamps(
        wav, model, sampling_rate=16000, return_seconds=True
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
