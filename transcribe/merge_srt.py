#!/usr/bin/env python3
"""
Merge several chunk SRT files into one continuous SRT.

Each long video is split into fixed-length audio chunks (e.g. 30 minutes) and
transcribed separately. Every chunk's subtitles start their clock at 00:00:00,
so before stitching them together we must shift each chunk's timestamps forward
by the amount of audio that came before it (its "offset").

Usage:
    python3 merge_srt.py MANIFEST OUTPUT.srt

MANIFEST is a text file with one chunk per line, tab-separated:
    /path/to/chunk_000.srt<TAB>0
    /path/to/chunk_001.srt<TAB>1800
    /path/to/chunk_002.srt<TAB>3600
The second column is the offset in SECONDS (may be fractional).

This script has no third-party dependencies so it runs on any Python 3.8+.
"""
import sys
import re

# Matches a single SRT cue's time line, e.g. "00:01:02,500 --> 00:01:05,000"
TIME_LINE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def ts_to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def ms_to_ts(total_ms):
    if total_ms < 0:
        total_ms = 0
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(text):
    """Return a list of (start_ms, end_ms, [text lines]) cues."""
    cues = []
    # Split into blocks separated by blank lines.
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        # Find the timing line (skip an optional leading index number).
        time_idx = None
        for i, line in enumerate(lines):
            if TIME_LINE.search(line):
                time_idx = i
                break
        if time_idx is None:
            continue
        match = TIME_LINE.search(lines[time_idx])
        start = ts_to_ms(*match.group(1, 2, 3, 4))
        end = ts_to_ms(*match.group(5, 6, 7, 8))
        body = [ln for ln in lines[time_idx + 1:] if ln.strip() != ""]
        if not body:
            continue
        cues.append((start, end, body))
    return cues


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: merge_srt.py MANIFEST OUTPUT.srt\n")
        sys.exit(2)

    manifest_path, out_path = sys.argv[1], sys.argv[2]

    all_cues = []
    with open(manifest_path, encoding="utf-8") as mf:
        for raw in mf:
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue
            parts = raw.split("\t")
            srt_path = parts[0]
            offset_ms = int(round(float(parts[1]) * 1000)) if len(parts) > 1 else 0
            try:
                with open(srt_path, encoding="utf-8") as sf:
                    text = sf.read()
            except FileNotFoundError:
                # An empty/silent chunk may produce no SRT; skip it gracefully.
                sys.stderr.write(f"warning: missing {srt_path}, skipping\n")
                continue
            for start, end, body in parse_srt(text):
                all_cues.append((start + offset_ms, end + offset_ms, body))

    # Keep chronological order; chunks are already ordered but be safe.
    all_cues.sort(key=lambda c: c[0])

    with open(out_path, "w", encoding="utf-8") as out:
        for idx, (start, end, body) in enumerate(all_cues, start=1):
            out.write(f"{idx}\n")
            out.write(f"{ms_to_ts(start)} --> {ms_to_ts(end)}\n")
            out.write("\n".join(body))
            out.write("\n\n")

    sys.stderr.write(f"merged {len(all_cues)} subtitle cues -> {out_path}\n")


if __name__ == "__main__":
    main()
