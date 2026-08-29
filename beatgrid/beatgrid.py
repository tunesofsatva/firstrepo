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
# Tempo estimation - a comb filter over the onset envelope.
#
# Rather than trust an individual beat tracker (which makes octave errors and
# miscounts in busy percussion), we fold the whole onset-strength signal at a
# candidate period and measure how concentrated the energy is at one phase.
# Summing over hundreds of beats makes the estimate both precise and robust.
# ---------------------------------------------------------------------------
TEMPO_CENTER = 128.0        # broad prior centre (dance/DJ music) for octave choice


def onset_envelope(y, sr):
    return librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)


def _comb_scores(oenv, frame_period, bpms):
    """For each candidate BPM, fold the onset envelope at that period into a
    phase histogram and return peak/mean - how concentrated the pulse is."""
    t = np.arange(len(oenv)) * frame_period
    scores = np.empty(len(bpms))
    for j, bpm in enumerate(bpms):
        p = 60.0 / bpm
        nb = max(4, int(round(p / frame_period)))
        b = np.floor(np.mod(t, p) / p * nb).astype(int)
        b[b >= nb] = nb - 1
        folded = np.bincount(b, weights=oenv, minlength=nb)
        scores[j] = folded.max() / (folded.mean() + 1e-9)
    return scores


def _tempo_prior(bpms, center, sigma=0.75):
    """Broad log-normal preference; resolves half/double/(2:3) octave ambiguity
    without pinning the exact value (it only nudges between metrical levels)."""
    return np.exp(-0.5 * (np.log2(np.asarray(bpms, float) / center) / sigma) ** 2)


def estimate_tempo(oenv, sr, bpm_min, bpm_max, coarse=0.1, fine=0.002,
                   center=TEMPO_CENTER):
    """Return (bpm, phase_sec): coarse-to-fine comb search weighted by the tempo
    prior, then a parabolically-refined phase (the first-beat offset)."""
    fp = HOP / sr
    grid = np.arange(bpm_min, bpm_max, coarse)
    s = _comb_scores(oenv, fp, grid) * _tempo_prior(grid, center)
    peak = grid[int(np.argmax(s))]
    fgrid = np.arange(max(bpm_min, peak - coarse), min(bpm_max, peak + coarse), fine)
    fs = _comb_scores(oenv, fp, fgrid) * _tempo_prior(fgrid, center)
    bpm = float(fgrid[int(np.argmax(fs))])
    # phase of the pulse: fold at the winning period, refine the peak bin
    p = 60.0 / bpm
    nb = max(4, int(round(p / fp)))
    t = np.arange(len(oenv)) * fp
    b = np.floor(np.mod(t, p) / p * nb).astype(int)
    b[b >= nb] = nb - 1
    folded = np.bincount(b, weights=oenv, minlength=nb)
    k = int(np.argmax(folded))
    a_, b_, c_ = folded[(k - 1) % nb], folded[k], folded[(k + 1) % nb]
    den = (a_ - 2 * b_ + c_)
    d = 0.5 * (a_ - c_) / den if den != 0 else 0.0
    phase = (((k + float(np.clip(d, -0.5, 0.5))) / nb) * p) % p
    return bpm, float(phase)


def local_tempo_curve(oenv, sr, bpm_global, win_sec=20.0, hop_sec=8.0, span=6.0):
    """Best tempo in each ~20 s window (centred on bpm_global so a window is not
    biased toward the prior). Returns (times_sec, bpm) arrays."""
    fp = HOP / sr
    W = int(win_sec / fp)
    H = max(1, int(hop_sec / fp))
    times, bpms = [], []
    for st in range(0, max(1, len(oenv) - W), H):
        seg = oenv[st:st + W]
        if len(seg) < W * 0.5:
            break
        b, _ = estimate_tempo(seg, sr, max(30.0, bpm_global - span),
                              bpm_global + span, coarse=0.05, fine=0.01,
                              center=bpm_global)
        times.append((st + W / 2) * fp)
        bpms.append(b)
    return np.asarray(times), np.asarray(bpms)


# ---------------------------------------------------------------------------
# Drift analysis + cue-point suggestions
# ---------------------------------------------------------------------------
def analyse_drift(oenv, sr, bpm_global, phase, drift_ms):
    """Track the local tempo across the song and integrate its departure from
    the single global BPM to get the end-to-end grid drift a DJ would actually
    see. Returns constant-ness, that drift figure, the local tempo range, and
    (if drifting) re-anchor cue points.
    """
    times, local = local_tempo_curve(oenv, sr, bpm_global)
    p_global = 60.0 / bpm_global

    if len(local) >= 2:
        f_global = bpm_global / 60.0
        dt = np.diff(times)
        f_mid = ((local[:-1] + local[1:]) / 2.0) / 60.0
        # beats gained/lost against the constant grid, accumulated over time
        cum_beats = np.concatenate([[0.0], np.cumsum((f_mid - f_global) * dt)])
        drift_series_ms = cum_beats * p_global * 1000.0
        drift_max_ms = float(np.max(np.abs(drift_series_ms)))
        spread = float(local.max() - local.min())
        lmin, lmax = float(local.min()), float(local.max())
    else:
        drift_series_ms = np.array([0.0])
        drift_max_ms = 0.0
        spread = 0.0
        lmin = lmax = float(bpm_global)

    is_constant = (drift_max_ms <= drift_ms) and (spread <= 0.8)

    # Cue points: re-anchor whenever the grid has slipped past the tolerance
    # since the last anchor. Each cue carries the local tempo from that point.
    cues = []
    if not is_constant and len(local) >= 2:
        cues.append({"time": float(phase % p_global),
                     "bpm": round(float(local[0]), 3)})
        anchor = 0.0
        for i in range(len(drift_series_ms)):
            if abs(drift_series_ms[i] - anchor) > drift_ms:
                cues.append({"time": float(times[i]),
                             "bpm": round(float(local[min(i, len(local) - 1)]), 3)})
                anchor = drift_series_ms[i]

    return {"is_constant": bool(is_constant),
            "drift_max_ms": round(drift_max_ms, 1),
            "local_bpm_min": round(lmin, 3),
            "local_bpm_max": round(lmax, 3),
            "bpm_spread": round(spread, 3),
            "cues": cues}


# ---------------------------------------------------------------------------
# Public analysis entry point
# ---------------------------------------------------------------------------
def analyze_file(path, bpm_min=70.0, bpm_max=180.0, drift_ms=25.0):
    if librosa is None:
        raise RuntimeError("librosa is not installed - run ./setup.sh first.")
    y, sr = decode_to_mono(path)
    duration = len(y) / sr
    if duration < 8:
        return {"file": os.path.basename(path), "error": "track too short",
                "duration_sec": round(duration, 1)}
    oenv = onset_envelope(y, sr)
    bpm, phase = estimate_tempo(oenv, sr, bpm_min, bpm_max)
    drift = analyse_drift(oenv, sr, bpm, phase, drift_ms)
    first_beat = float(phase % (60.0 / bpm))     # a real beat near the start
    return {
        "file": os.path.basename(path),
        "path": path,
        "duration_sec": round(duration, 1),
        "bpm": round(bpm, 3),
        "bpm_rounded": round(bpm),
        "first_beat_sec": round(first_beat, 3),
        "first_beat_mmss": sec_to_mmss(first_beat),
        "beats_detected": int(round(duration / (60.0 / bpm))),
        "verdict": "constant" if drift["is_constant"] else "drifting",
        "drift": drift,
        "params": {"drift_ms": drift_ms, "bpm_min": bpm_min, "bpm_max": bpm_max},
    }


# ---------------------------------------------------------------------------
# Warp: build a rubberband time-map from the local tempo curve, so the whole
# track ends up at a single constant tempo.
# ---------------------------------------------------------------------------
def build_timemap_from_tempo(times, local_bpm, duration, sr_out, target_bpm):
    """Map source time -> output time so the varying local tempo becomes a
    constant target_bpm:  output_time(t) = (beats elapsed by t) / target_beats.
    Returns (source_sample, target_sample) pairs for rubberband to interpolate.
    """
    tt = np.arange(0.0, duration, 0.05)
    f = np.interp(tt, times, local_bpm,
                  left=local_bpm[0], right=local_bpm[-1]) / 60.0
    beats = np.concatenate([[0.0], np.cumsum((f[:-1] + f[1:]) / 2.0 * np.diff(tt))])
    out_t = beats / (target_bpm / 60.0)
    pairs = [(0, 0)]
    for i in range(len(tt)):
        s = int(round(tt[i] * sr_out))
        d = int(round(out_t[i] * sr_out))
        if s > pairs[-1][0] and d > pairs[-1][1]:
            pairs.append((s, d))
    return pairs


def _run_rubberband(mapfile, pairs, src_wav, out_wav):
    """Run rubberband with a time map. The CLI REQUIRES an overall stretch
    factor (-t) alongside --timemap; we derive it from the map's endpoints.
    Raises a concise error instead of letting rubberband dump its help."""
    last_src = max(1, pairs[-1][0])
    ratio = pairs[-1][1] / last_src            # total output / total input
    res = subprocess.run(
        ["rubberband", "-t", f"{ratio:.9f}", "--timemap", mapfile,
         "-3", src_wav, out_wav],          # -3 = R3 (finest) engine, best quality
        capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(out_wav):
        msg = (res.stderr or res.stdout or "").strip().splitlines()
        raise RuntimeError("rubberband failed: " +
                           (msg[0] if msg else f"exit {res.returncode}"))


def warp_file(path, target_bpm, out_path, bpm_min=70.0, bpm_max=180.0):
    """Render a new lossless file whose tempo is a constant target_bpm."""
    if librosa is None:
        raise RuntimeError("librosa is not installed - run ./setup.sh first.")
    if not _have("rubberband"):
        raise RuntimeError(
            "rubberband is not installed. Run:  brew install rubberband")
    sr_out = 44100
    y, sr = decode_to_mono(path, ANALYSIS_SR)
    duration = len(y) / sr
    oenv = onset_envelope(y, sr)
    bpm, _phase = estimate_tempo(oenv, sr, bpm_min, bpm_max)
    times, local = local_tempo_curve(oenv, sr, bpm)
    if len(local) < 2:                            # essentially constant already
        times = np.array([0.0, duration])
        local = np.array([bpm, bpm])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        src_wav = tf.name
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        mapfile = tf.name
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path,
                        "-ar", str(sr_out), src_wav], check=True)
        pairs = build_timemap_from_tempo(times, local, duration, sr_out, target_bpm)
        with open(mapfile, "w") as f:
            for s, t in pairs:
                f.write(f"{s} {t}\n")
        _run_rubberband(mapfile, pairs, src_wav, out_path)
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
