#!/usr/bin/env python3
"""
Turn a finished .srt subtitle file into a readable Markdown transcript.

The Markdown keeps timestamps, which makes it easy for Claude (or you) to
jump to or cite a specific moment in the recording.

Usage:
    python3 srt_to_md.py INPUT.srt "Title" OUTPUT.md
"""
import sys
import re

TIME_LINE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def parse_srt(text):
    cues = []
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    for block in blocks:
        lines = block.splitlines()
        time_idx = None
        for i, line in enumerate(lines):
            if TIME_LINE.search(line):
                time_idx = i
                break
        if time_idx is None:
            continue
        m = TIME_LINE.search(lines[time_idx])
        start = f"{m.group(1)}:{m.group(2)}:{m.group(3)}"  # HH:MM:SS
        body = " ".join(
            ln.strip() for ln in lines[time_idx + 1:] if ln.strip()
        )
        if body:
            cues.append((start, body))
    return cues


def main():
    if len(sys.argv) != 4:
        sys.stderr.write('usage: srt_to_md.py INPUT.srt "Title" OUTPUT.md\n')
        sys.exit(2)

    srt_path, title, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(srt_path, encoding="utf-8") as f:
        cues = parse_srt(f.read())

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"# {title}\n\n")
        out.write("_Transcript generated locally with MLX-Whisper._\n\n")
        out.write("---\n\n")
        for start, body in cues:
            out.write(f"**[{start}]** {body}\n\n")

    sys.stderr.write(f"wrote {len(cues)} timestamped lines -> {out_path}\n")


if __name__ == "__main__":
    main()
