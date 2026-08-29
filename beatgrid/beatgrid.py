#!/usr/bin/env python3
"""
beatgrid - find the exact BPM and beat-grid anchor for a track, detect tempo
drift, and (optionally) suggest cue points or warp the audio to a perfectly
even grid.

This is the analysis engine. You normally run it through the friendly wrapper
scripts (./analyze.sh, ./scan.sh, ./warp.sh), but you can also call it directly:

    python3 beatgrid.py analyze  input/track.mp3
    python3 beatgrid.py scan     ~/Music/DJ
    python3 beatgrid.py warp     input/track.mp3 --bpm 128

What it does, in plain terms
----------------------------
DJ software draws a "beat grid" of evenly spaced lines and assumes ONE constant
BPM. Two things break that:

  1. The real tempo isn't a round number (it's 127.96, not 128). You set 128,
     and the grid slowly slides out of the beat - "goes forward, then backward".
  2. The tempo actually drifts through the track (live drummer, old record,
     no click). No single BPM can ever line up the whole song.

beatgrid measures the ACTUAL beat positions and:
  * reports the precise BPM to type in (fixes case 1 completely), plus the
    exact time of the first downbeat to anchor the grid on;
  * tells you whether the track is genuinely constant or drifting;
  * if it drifts, suggests "reset" cue points - a time + a new local BPM for
    each stretch that holds steady before it drifts again;
  * can also render a new lossless file warped to a perfectly even grid, so
    any constant BPM lines up for the whole track.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

# librosa is only needed for the audio analysis, not for the pure-math helpers,
# so import it lazily and give a friendly message if setup wasn't run.
try:
    import librosa
except Exception:  # pragma: no cover - only hit before ./setup.sh
    librosa = None

ANALYSIS_SR = 22050          # sample rate we analyse at (plenty for beats)
HOP = 256                    # onset-envelope hop: ~11.6 ms resolution at 22050
AUDIO_EXTS = (".mp3", ".m4a", ".wav", ".aiff", ".aif", ".flac", ".aac",
              ".mp4", ".m4v", ".mov", ".ogg", ".wma")


# ---------------------------------------------------------------------------
# Audio loading (via ffmpeg, so every format the user throws at us just works)
# ---------------------------------------------------------------------------
def decode_to_mono(path, sr=ANALYSIS_SR):
    """Decode any audio/video file to a mono float32 numpy array at `sr`.

    We shell out to ffmpeg (installed by setup.sh) rather than leaning on
    librosa's own mp3/m4a decoding, which is fragile across platforms.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    # Fast path: a WAV can be read without ffmpeg at all.
    if path.lower().endswith(".wav"):
        try:
            import soundfile as sf
            data, in_sr = sf.read(path, dtype="float32", always_2d=True)
            y = data.mean(axis=1)                      # mix to mono
            if in_sr != sr:
                y = librosa.resample(y, orig_sr=in_sr, target_sr=sr)
            return y.astype(np.float32), sr
        except Exception:
            pass                                       # fall back to ffmpeg
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp = tf.name
    try:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", path,
               "-ac", "1", "-ar", str(sr), "-f", "wav", tmp]
        subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with wave.open(tmp, "rb") as w:
            n = w.getnframes()
            raw = w.readframes(n)
            width = w.getsampwidth()
        if width == 2:
            y = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif width == 4:
            y = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            y = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            y = (y - 128.0) / 128.0
        return y, sr
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Beat detection
# ---------------------------------------------------------------------------
def detect_beat_times(y, sr):
    """Return (beat_times, onset_env, oenv_times, tempo_guess).

    Beat times are refined to sub-frame precision by fitting a parabola to the
    onset-strength peak around each beat, so we aren't limited to the ~12 ms
    frame grid - that precision is what lets us pin the BPM down to a few
    thousandths.
    """
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    tempo, beats = librosa.beat.beat_track(
        onset_envelope=oenv, sr=sr, hop_length=HOP, trim=False)
    tempo = float(np.atleast_1d(tempo)[0])
    frame_period = HOP / sr
    times = []
    for f in beats:
        f = int(f)
        # parabolic interpolation around the onset peak for sub-frame accuracy
        if 0 < f < len(oenv) - 1:
            a, b, c = oenv[f - 1], oenv[f], oenv[f + 1]
            denom = (a - 2 * b + c)
            delta = 0.5 * (a - c) / denom if denom != 0 else 0.0
            delta = float(np.clip(delta, -0.5, 0.5))
        else:
            delta = 0.0
        times.append((f + delta) * frame_period)
    times = np.asarray(times, dtype=np.float64)
    oenv_times = np.arange(len(oenv)) * frame_period
    return times, oenv, oenv_times, tempo


# ---------------------------------------------------------------------------
# The core: fit a single constant grid to the detected beats
# ---------------------------------------------------------------------------
def robust_grid_fit(times, period0):
    """Fit  time = anchor + period * beat_index  robustly.

    Beat indices are recovered by cumulative rounding against an initial period
    (so a missed/extra beat doesn't throw the whole line off), then we do
    least-squares with iterative outlier rejection.

    Returns dict with anchor, period, bpm, idx, resid, keep(mask).
    """
    times = np.asarray(times, dtype=np.float64)
    n = len(times)
    idx = np.zeros(n)
    for i in range(1, n):
        step = round((times[i] - times[i - 1]) / period0)
        idx[i] = idx[i - 1] + max(1, step)

    keep = np.ones(n, dtype=bool)
    period = period0
    anchor = times[0]
    for _ in range(6):
        b, a = np.polyfit(idx[keep], times[keep], 1)  # slope=period, intercept=anchor
        period, anchor = float(b), float(a)
        resid = times - (anchor + period * idx)
        med = np.median(resid[keep])
        mad = np.median(np.abs(resid[keep] - med)) + 1e-9
        new_keep = np.abs(resid - med) < 5 * 1.4826 * mad
        if new_keep.sum() < max(4, 0.5 * n):
            break
        if np.array_equal(new_keep, keep):
            keep = new_keep
            break
        keep = new_keep

    resid = times - (anchor + period * idx)
    return {"anchor": anchor, "period": period, "bpm": 60.0 / period,
            "idx": idx, "resid": resid, "keep": keep}


def choose_octave(times, tempo_guess, bpm_min, bpm_max):
    """Try the tempo guess and its half/double, keep the best musical fit."""
    period0 = 60.0 / tempo_guess if tempo_guess > 0 else np.median(np.diff(times))
    candidates = []
    for mult in (0.5, 1.0, 2.0):
        p = period0 / mult
        fit = robust_grid_fit(times, p)
        bpm = fit["bpm"]
        # normalise into the requested range by octave folding
        while bpm < bpm_min - 1e-6:
            bpm *= 2
        while bpm > bpm_max + 1e-6:
            bpm /= 2
        in_range = bpm_min - 1e-6 <= bpm <= bpm_max + 1e-6
        rms = float(np.sqrt(np.mean(fit["resid"][fit["keep"]] ** 2)))
        candidates.append((in_range, -rms, fit))
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return candidates[0][2]


# ---------------------------------------------------------------------------
# Drift analysis + cue-point suggestions
# ---------------------------------------------------------------------------
def analyse_drift(times, fit, drift_ms, sr):
    """Measure how the constant grid drifts away from the real beats and, if it
    drifts past `drift_ms`, propose re-anchor (cue) points.

    Returns dict describing constant-ness and a list of cue segments.
    """
    anchor, period = fit["anchor"], fit["period"]
    idx, keep = fit["idx"], fit["keep"]
    good = keep
    t = times[good]
    k = idx[good]

    # local BPM via a sliding-window linear fit (window ~ 16 beats)
    win = 16
    local_bpm_times, local_bpm = [], []
    for i in range(len(t)):
        lo = max(0, i - win // 2)
        hi = min(len(t), i + win // 2 + 1)
        if hi - lo >= 4:
            slope = np.polyfit(k[lo:hi], t[lo:hi], 1)[0]
            local_bpm_times.append(t[i])
            local_bpm.append(60.0 / slope)
    local_bpm = np.asarray(local_bpm)

    # drift of each real beat away from the ONE constant grid anchored at start
    grid = anchor + period * k
    drift = t - grid                      # seconds; +ve = beat later than grid
    rms_ms = float(np.sqrt(np.mean((drift * 1000) ** 2)))
    max_ms = float(np.max(np.abs(drift)) * 1000)

    bpm_spread = float(local_bpm.max() - local_bpm.min()) if len(local_bpm) else 0.0
    # "constant" if the whole track stays within the tolerance and local tempo
    # barely moves
    is_constant = (max_ms <= drift_ms) and (bpm_spread <= 0.6)

    # Build cue segments: walk beats, re-anchor whenever the beats drift past
    # the tolerance away from the CURRENT segment's own even grid. A minimum
    # segment length keeps us from emitting useless 2-3 beat slivers.
    min_beats = 8
    cues = []
    seg_start = 0
    while seg_start < len(t) - min_beats:
        end = seg_start + min_beats            # every segment is at least this long
        while end < len(t):
            local_period = np.polyfit(k[seg_start:end + 1],
                                      t[seg_start:end + 1], 1)[0]
            gr = t[seg_start] + local_period * (k[seg_start:end + 1] - k[seg_start])
            if np.max(np.abs(t[seg_start:end + 1] - gr)) * 1000 > drift_ms:
                break
            end += 1
        seg_slope = np.polyfit(k[seg_start:end], t[seg_start:end], 1)[0]
        cues.append({"time": float(t[seg_start]),
                     "bpm": round(60.0 / seg_slope, 3),
                     "beats": int(k[min(end, len(k) - 1)] - k[seg_start])})
        if end >= len(t) - min_beats:
            break
        seg_start = end

    return {"is_constant": bool(is_constant),
            "drift_rms_ms": round(rms_ms, 1),
            "drift_max_ms": round(max_ms, 1),
            "local_bpm_min": round(float(local_bpm.min()), 3) if len(local_bpm) else None,
            "local_bpm_max": round(float(local_bpm.max()), 3) if len(local_bpm) else None,
            "bpm_spread": round(bpm_spread, 3),
            "cues": cues}


# ---------------------------------------------------------------------------
# Public analysis entry point
# ---------------------------------------------------------------------------
def analyze_file(path, bpm_min=70.0, bpm_max=180.0, drift_ms=25.0):
    if librosa is None:
        raise RuntimeError("librosa is not installed - run ./setup.sh first.")
    y, sr = decode_to_mono(path)
    duration = len(y) / sr
    times, oenv, oenv_times, tempo_guess = detect_beat_times(y, sr)
    if len(times) < 8:
        return {"file": os.path.basename(path), "error": "too few beats detected",
                "duration_sec": round(duration, 1)}
    fit = choose_octave(times, tempo_guess, bpm_min, bpm_max)
    drift = analyse_drift(times, fit, drift_ms, sr)

    # fold the reported BPM into the requested range too
    bpm = fit["bpm"]
    anchor = fit["anchor"]
    period = fit["period"]
    while bpm < bpm_min - 1e-6:
        bpm *= 2
        period /= 2
    while bpm > bpm_max + 1e-6:
        bpm /= 2
        period *= 2
    # bring the anchor (first downbeat) to the first real beat within one bar
    first_beat = float(times[fit["keep"]][0])

    return {
        "file": os.path.basename(path),
        "path": path,
        "duration_sec": round(duration, 1),
        "bpm": round(bpm, 3),
        "bpm_rounded": round(bpm),
        "first_beat_sec": round(first_beat, 3),
        "first_beat_mmss": sec_to_mmss(first_beat),
        "beats_detected": int(len(times)),
        "grid_fit_rms_ms": round(float(np.sqrt(np.mean(
            (fit["resid"][fit["keep"]] * 1000) ** 2))), 1),
        "verdict": "constant" if drift["is_constant"] else "drifting",
        "drift": drift,
        "params": {"drift_ms": drift_ms, "bpm_min": bpm_min, "bpm_max": bpm_max},
    }


# ---------------------------------------------------------------------------
# Warp: build a rubberband time-map that pins beats onto an even grid
# ---------------------------------------------------------------------------
def build_timemap(beat_source_samples, target_bpm, sr_out, total_samples):
    """Return list of (source_sample, target_sample) mapping detected beats onto
    a perfectly even grid at target_bpm. rubberband interpolates between them.
    """
    samples_per_beat = sr_out * 60.0 / target_bpm
    pairs = [(0, 0)]
    first = beat_source_samples[0]
    for i, s in enumerate(beat_source_samples):
        src = int(round(s))
        tgt = int(round(first + i * samples_per_beat))
        if src > pairs[-1][0] and tgt > pairs[-1][1]:
            pairs.append((src, tgt))
    # extend to the end at the last known local ratio
    last_src, last_tgt = pairs[-1]
    if total_samples > last_src:
        ratio = (pairs[-1][1] - pairs[-2][1]) / max(1, (pairs[-1][0] - pairs[-2][0]))
        pairs.append((int(total_samples),
                      int(last_tgt + ratio * (total_samples - last_src))))
    return pairs


def warp_file(path, target_bpm, out_path, bpm_min=70.0, bpm_max=180.0):
    """Render a new lossless file whose beats are perfectly even at target_bpm."""
    if librosa is None:
        raise RuntimeError("librosa is not installed - run ./setup.sh first.")
    if not _have("rubberband"):
        raise RuntimeError(
            "rubberband is not installed. Run:  brew install rubberband")
    sr_out = 44100
    # detect beats at analysis rate, then map their times to output samples
    y, sr = decode_to_mono(path, ANALYSIS_SR)
    times, *_rest = detect_beat_times(y, sr)
    tempo_guess = _rest[-1]
    fit = choose_octave(times, tempo_guess, bpm_min, bpm_max)
    beat_times = times[fit["keep"]]
    beat_src_samples = beat_times * sr_out

    # decode a clean 44.1k stereo wav to feed rubberband
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        src_wav = tf.name
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        mapfile = tf.name
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path,
                        "-ar", str(sr_out), src_wav], check=True)
        with wave.open(src_wav, "rb") as w:
            total = w.getnframes()
        pairs = build_timemap(beat_src_samples, target_bpm, sr_out, total)
        with open(mapfile, "w") as f:
            for s, t in pairs:
                f.write(f"{s} {t}\n")
        # rubberband with an explicit time map; -c 6 = crisp/percussive settings
        subprocess.run(["rubberband", "--timemap", mapfile, "-c", "6",
                        src_wav, out_path], check=True)
        return out_path
    finally:
        for p in (src_wav, mapfile):
            try:
                os.remove(p)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def sec_to_mmss(s):
    m = int(s // 60)
    return f"{m}:{s - 60 * m:06.3f}"


def _have(cmd):
    from shutil import which
    return which(cmd) is not None


def format_report(r):
    if "error" in r:
        return f"{r['file']}: could not analyse ({r['error']})"
    lines = []
    lines.append(f"  Track      : {r['file']}")
    lines.append(f"  Length     : {sec_to_mmss(r['duration_sec'])}  "
                 f"({r['beats_detected']} beats detected)")
    lines.append(f"  BPM to set : {r['bpm']:.3f}   (nearest whole number: {r['bpm_rounded']})")
    lines.append(f"  Anchor grid: first downbeat at {r['first_beat_mmss']}  "
                 f"({r['first_beat_sec']} s)")
    d = r["drift"]
    if r["verdict"] == "constant":
        lines.append(f"  Verdict    : CONSTANT tempo. In Traktor: set BPM = "
                     f"{r['bpm']:.3f} and put the grid marker on the first "
                     f"downbeat - it lines up for the whole track.")
        lines.append(f"               (grid stays within {d['drift_max_ms']} ms "
                     f"of the beat end-to-end)")
    else:
        lines.append(f"  Verdict    : DRIFTING tempo (varies "
                     f"{d['local_bpm_min']}-{d['local_bpm_max']} BPM; the grid "
                     f"wanders up to {d['drift_max_ms']} ms off the beat).")
        lines.append(f"               No single BPM can hold. Traktor uses ONE "
                     f"fixed grid per track, so the clean fix is to WARP it:")
        lines.append(f"                   ./warp.sh \"{r['file']}\" "
                     f"{r['bpm_rounded']}")
        lines.append(f"               then set BPM {r['bpm_rounded']} and one grid "
                     f"marker on beat 1.")
        lines.append(f"               Section tempos below are for reference / "
                     f"manual hotcues (Traktor hotcues do NOT re-grid the track):")
        for i, c in enumerate(d["cues"], 1):
            lines.append(f"                   {sec_to_mmss(c['time'])}"
                         f"   -> {c['bpm']:.3f} BPM")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_analyze(args):
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    for path in args.files:
        try:
            r = analyze_file(path, args.bpm_min, args.bpm_max, args.drift_ms)
        except Exception as e:  # keep going through a batch
            print(f"\n{os.path.basename(path)}: ERROR - {e}", file=sys.stderr)
            continue
        print()
        print(format_report(r))
        base = os.path.splitext(os.path.basename(path))[0]
        with open(os.path.join(outdir, base + ".beatgrid.json"), "w") as f:
            json.dump(r, f, indent=2)
        with open(os.path.join(outdir, base + ".beatgrid.txt"), "w") as f:
            f.write(format_report(r) + "\n")
    print()


def cmd_scan(args):
    root = args.dir
    files = []
    for dp, _dn, fn in os.walk(root):
        for name in fn:
            if name.lower().endswith(AUDIO_EXTS) and not name.startswith("."):
                files.append(os.path.join(dp, name))
    files.sort()
    print(f"Scanning {len(files)} tracks under {root} ...\n")
    rows = []
    for path in files:
        try:
            r = analyze_file(path, args.bpm_min, args.bpm_max, args.drift_ms)
        except Exception as e:
            print(f"  SKIP {os.path.basename(path)}: {e}", file=sys.stderr)
            continue
        if "error" in r:
            continue
        rows.append(r)
        flag = "OK      " if r["verdict"] == "constant" else ">> DRIFT"
        print(f"  {flag}  {r['bpm']:7.3f} BPM  drift<= {r['drift']['drift_max_ms']:5.0f}ms"
              f"   {r['file']}")
    # summary CSV
    csv = os.path.join(args.out, "library-scan.csv")
    os.makedirs(args.out, exist_ok=True)
    with open(csv, "w") as f:
        f.write("file,bpm,bpm_rounded,verdict,drift_max_ms,local_bpm_min,"
                "local_bpm_max,first_beat_sec,duration_sec\n")
        for r in rows:
            d = r["drift"]
            f.write(f"\"{r['file']}\",{r['bpm']},{r['bpm_rounded']},{r['verdict']},"
                    f"{d['drift_max_ms']},{d['local_bpm_min']},{d['local_bpm_max']},"
                    f"{r['first_beat_sec']},{r['duration_sec']}\n")
    drift = [r for r in rows if r["verdict"] == "drifting"]
    print(f"\nDone. {len(rows)} analysed, {len(drift)} drifting / out of sync.")
    print(f"Full table: {csv}")


def cmd_warp(args):
    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.file))[0]
    if args.bpm:
        target = float(args.bpm)
    else:
        r = analyze_file(args.file, args.bpm_min, args.bpm_max, args.drift_ms)
        target = float(r["bpm_rounded"])
        print(f"No BPM given; warping to detected whole-number BPM = {target}")
    out_path = os.path.join(args.out, f"{base} [{target:g} warped].wav")
    print(f"Warping {args.file} -> perfectly even {target:g} BPM ...")
    warp_file(args.file, target, out_path, args.bpm_min, args.bpm_max)
    print(f"Wrote {out_path}")


def cmd_nml(args):
    import traktor_nml
    traktor_nml.process(
        args.collection, analyze_fn=analyze_file,
        apply=args.apply, in_place=args.in_place, check=args.check,
        only_under=args.only_under, drift=args.drift, warp_fn=warp_file,
        out_dir=args.out, bpm_min=args.bpm_min, bpm_max=args.bpm_max,
        drift_ms=args.drift_ms, limit=args.limit)


def main(argv=None):
    p = argparse.ArgumentParser(prog="beatgrid", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--bpm-min", dest="bpm_min", type=float, default=70.0)
    common.add_argument("--bpm-max", dest="bpm_max", type=float, default=180.0)
    common.add_argument("--drift-ms", dest="drift_ms", type=float, default=25.0,
                        help="how far (ms) the grid may drift before it counts "
                             "as out of sync / a new cue is suggested")
    common.add_argument("--out", default="output")

    pa = sub.add_parser("analyze", parents=[common], help="analyse one or more files")
    pa.add_argument("files", nargs="+")
    pa.set_defaults(func=cmd_analyze)

    ps = sub.add_parser("scan", parents=[common], help="scan a whole folder")
    ps.add_argument("dir")
    ps.set_defaults(func=cmd_scan)

    pw = sub.add_parser("warp", parents=[common], help="render an even-grid copy")
    pw.add_argument("file")
    pw.add_argument("--bpm", default=None, help="target BPM (default: detected)")
    pw.set_defaults(func=cmd_warp)

    pn = sub.add_parser("nml", parents=[common],
                        help="write BPM + grid markers into a Traktor collection.nml")
    pn.add_argument("--collection", required=True, help="path to collection.nml")
    pn.add_argument("--check", action="store_true",
                    help="only decode & list paths (confirm before writing)")
    pn.add_argument("--apply", action="store_true",
                    help="actually write (default is a dry run)")
    pn.add_argument("--in-place", dest="in_place", action="store_true",
                    help="overwrite collection.nml (makes a .bak); default writes "
                         "a new collection.beatgrid.nml")
    pn.add_argument("--only-under", dest="only_under", default=None,
                    help="limit to tracks whose file lives under this folder")
    pn.add_argument("--drift", choices=["warp", "skip"], default="warp",
                    help="drifting tracks: render a warped copy (default) or skip")
    pn.add_argument("--limit", type=int, default=None,
                    help="process at most N tracks (handy for a first test)")
    pn.set_defaults(func=cmd_nml)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
