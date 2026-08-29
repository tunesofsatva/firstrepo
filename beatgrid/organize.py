#!/usr/bin/env python3
"""
organize - the simple, whole-library front end for beatgrid.

Two steps, nothing else to think about:

  1) SCAN  -> makes ONE Excel sheet listing every track in your folder(s),
              each labelled GOOD / WRONG NUMBER / DRIFTS, with the current and
              correct BPM. Changes nothing on disk.

  2) FIX   -> WRONG NUMBER tracks: corrected inside Traktor (no new file).
              DRIFTS tracks: a straightened lossless copy is written next to the
              original (tags, artwork and your cue points carried over). The
              Excel sheet is updated with the new files, and a delete-old script
              is written for you to run after you've listened.

Your original files are never modified. Nothing is ever deleted by this tool -
it only writes new files and a delete script that YOU choose to run.
"""

import os
import subprocess
import time
import xml.etree.ElementTree as ET

import beatgrid as bg
import traktor_nml as tn

BPM_TOL = 0.03                     # closer than this to correct = already fine
STATUS_COLORS = {                  # for the Excel sheet
    "GOOD": "C6EFCE", "WRONG NUMBER": "FFEB9C", "DRIFTS": "FFC7CE",
    "STEADY": "DDEBF7", "SKIP": "D9D9D9",
}


# ---------------------------------------------------------------------------
# Finding files and reading the Traktor collection
# ---------------------------------------------------------------------------
def find_audio(folders):
    files = []
    for folder in folders:
        folder = os.path.expanduser(folder)
        if os.path.isfile(folder):
            files.append(folder)
            continue
        for dp, _dn, fn in os.walk(folder):
            for n in fn:
                if n.lower().endswith(bg.AUDIO_EXTS) and not n.startswith("."):
                    files.append(os.path.join(dp, n))
    return sorted(files)


def index_collection(nml_path):
    """Return (index, tree). index maps normalised file path -> dict with the
    ENTRY element, its current BPM, and how many of your cue points it has."""
    index = {}
    if not nml_path:
        return index, None
    nml_path = os.path.expanduser(nml_path)
    if not os.path.exists(nml_path):
        return index, None
    tree = ET.parse(nml_path)
    col = tree.getroot().find("COLLECTION")
    if col is None:
        return index, tree
    for e in col.findall("ENTRY"):
        loc = e.find("LOCATION")
        if loc is None:
            continue
        p = os.path.normpath(tn.location_to_path(loc))
        t = e.find("TEMPO")
        bpm = float(t.get("BPM")) if (t is not None and t.get("BPM")) else None
        cues = sum(1 for c in e.findall("CUE_V2") if c.get("TYPE") == "0")
        index[p] = {"entry": e, "bpm": bpm, "cues": cues}
    return index, tree


def classify(r, current_bpm):
    """Return (status, correct_bpm)."""
    if "error" in r:
        return "SKIP", None
    correct = r["bpm"]
    if r["verdict"] == "drifting":
        return "DRIFTS", correct
    if current_bpm is None:
        return "STEADY", correct          # steady, but not found in Traktor
    if abs(current_bpm - correct) > BPM_TOL:
        return "WRONG NUMBER", correct
    return "GOOD", correct


# ---------------------------------------------------------------------------
# STEP 1: scan -> Excel + txt
# ---------------------------------------------------------------------------
def scan(folders, out_dir, collection=None, drift_ms=25.0):
    files = find_audio(folders)
    index, _ = index_collection(collection)
    print(f"Found {len(files)} tracks. Analysing "
          f"{'(with your Traktor collection)' if index else '(no collection given)'}...\n")
    rows = []
    for p in files:
        try:
            r = bg.analyze_file(p, drift_ms=drift_ms)
        except Exception as ex:
            rows.append({"name": os.path.basename(p), "folder": os.path.dirname(p),
                         "path": p, "status": "SKIP", "cur": None, "correct": None,
                         "drift": None, "first_beat": None, "cues": 0,
                         "note": str(ex)})
            print(f"  SKIP         {os.path.basename(p)}: {ex}")
            continue
        info = index.get(os.path.normpath(p))
        cur = info["bpm"] if info else None
        status, correct = classify(r, cur)
        rows.append({"name": os.path.basename(p), "folder": os.path.dirname(p),
                     "path": p, "status": status, "cur": cur, "correct": correct,
                     "drift": r.get("drift", {}).get("drift_max_ms"),
                     "first_beat": r.get("first_beat_sec"),
                     "cues": info["cues"] if info else 0, "note": ""})
        c = f"{correct:.3f}" if correct else ""
        n = f"  (you have {info['cues']} cue pts)" if info and info["cues"] else ""
        print(f"  {status:12} correct={c:>8}  {os.path.basename(p)}{n}")
    os.makedirs(out_dir, exist_ok=True)
    xlsx = os.path.join(out_dir, "beatgrid-report.xlsx")
    txt = os.path.join(out_dir, "beatgrid-report.txt")
    write_xlsx(rows, xlsx)
    write_txt(rows, txt)
    _summary(rows)
    print(f"\nExcel list : {xlsx}")
    print(f"Text list  : {txt}")
    return rows


def _summary(rows):
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    print("\n---------------- SUMMARY ----------------")
    print(f"  GOOD (leave alone)        : {c.get('GOOD', 0)}")
    print(f"  WRONG NUMBER (fix in Traktor): {c.get('WRONG NUMBER', 0)}")
    print(f"  DRIFTS (make a fixed copy): {c.get('DRIFTS', 0)}")
    if c.get("STEADY"):
        print(f"  STEADY, not in Traktor yet: {c.get('STEADY', 0)}")
    if c.get("SKIP"):
        print(f"  could not read            : {c.get('SKIP', 0)}")
    print("-----------------------------------------")


def write_txt(rows, path):
    with open(path, "w") as f:
        f.write("beatgrid report\n\n")
        for r in rows:
            cur = f"{r['cur']:.3f}" if r["cur"] else "-"
            cor = f"{r['correct']:.3f}" if r["correct"] else "-"
            f.write(f"[{r['status']:12}] now={cur:>8} correct={cor:>8}  "
                    f"{r['name']}\n      {r['path']}\n")


def write_xlsx(rows, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "beatgrid"
    headers = ["#", "Track", "Status", "What to do", "Now BPM (Traktor)",
               "Correct BPM", "Your cue pts", "Folder", "Original file (full path)",
               "Fixed file (after step 2)", "Listened?", "Delete original?"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="404040")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    todo = {"GOOD": "nothing - it's fine",
            "WRONG NUMBER": "step 2 fixes the number in Traktor",
            "DRIFTS": "step 2 makes a fixed copy - listen, then delete old",
            "STEADY": "not in Traktor; set Correct BPM if you add it",
            "SKIP": "could not read this file"}
    for i, r in enumerate(rows, 1):
        ws.append([i, r["name"], r["status"], todo.get(r["status"], ""),
                   round(r["cur"], 3) if r["cur"] else "",
                   round(r["correct"], 3) if r["correct"] else "",
                   r["cues"] or "", r["folder"], r["path"], "", "", ""])
        fill = STATUS_COLORS.get(r["status"])
        if fill:
            ws.cell(row=i + 1, column=3).fill = PatternFill("solid", fgColor=fill)
    widths = [4, 42, 14, 34, 15, 12, 11, 30, 52, 46, 11, 15]
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=j).column_letter].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


# ---------------------------------------------------------------------------
# STEP 2: fix
# ---------------------------------------------------------------------------
LOSSY_EXTS = (".mp3", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".m4v", ".mov")


def _mux_tags(warped_wav, original, out_path):
    """Mux the straightened audio with all tags + artwork from the original.
    Match the source: a lossy source -> AAC 320k (keeps file size similar);
    a lossless source (wav/flac/aiff) -> ALAC lossless."""
    if original.lower().endswith(LOSSY_EXTS):
        acodec = ["-c:a", "aac", "-b:a", "320k"]
    else:
        acodec = ["-c:a", "alac"]
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-i", warped_wav, "-i", original,
           "-map", "0:a", "-map_metadata", "1"] + acodec
    cmd += ["-map", "1:v?", "-c:v", "copy", "-disposition:v", "attached_pic"]
    cmd += [out_path]
    subprocess.run(cmd, check=True)


def fix(folders, out_dir, collection, drift_ms=25.0, apply=False, warp_drift=False):
    files = find_audio(folders)
    index, tree = index_collection(collection)
    if collection and tree is None:
        raise RuntimeError(f"Could not read collection: {collection}")
    os.makedirs(out_dir, exist_ok=True)

    fixed_new_files = []     # (original_path, new_path)
    changed = 0
    print(f"{'APPLYING' if apply else 'DRY RUN (nothing written yet)'}\n")

    for p in files:
        try:
            r = bg.analyze_file(p, drift_ms=drift_ms)
        except Exception as ex:
            print(f"  SKIP {os.path.basename(p)}: {ex}")
            continue
        if "error" in r:
            continue
        info = index.get(os.path.normpath(p))
        cur = info["bpm"] if info else None
        status, correct = classify(r, cur)

        if status in ("GOOD", "SKIP"):
            continue

        # By default, DRIFTS tracks are ALSO just number-fixed (no new file, no
        # quality loss, all metadata/cues kept). Only warp them when asked.
        if status == "WRONG NUMBER" or (status == "DRIFTS" and not warp_drift):
            if info is None:
                print(f"  (not in Traktor, skipping) {os.path.basename(p)}")
                continue
            tag = "FIX NUMBER" if status == "WRONG NUMBER" else "SET BPM (drift remains)"
            curtxt = f"{cur:.3f}" if cur is not None else "?"
            print(f"  {tag}  {curtxt} -> {correct:.3f}   {os.path.basename(p)}")
            if apply:
                tn.set_tempo(info["entry"], correct)
                tn.set_grid_marker(info["entry"], r["first_beat_sec"])
            changed += 1

        elif status == "DRIFTS" and warp_drift:
            base, _ext = os.path.splitext(p)
            target = float(round(correct))
            new_path = f"{base} (fixed {target:g}).m4a"
            print(f"  STRAIGHTEN  -> {os.path.basename(new_path)}  (to {target:g} BPM)")
            if apply:
                try:
                    _make_fixed_copy(p, target, new_path, r, drift_ms)
                    fixed_new_files.append((p, new_path))
                    if info is not None and tree is not None:
                        _add_fixed_entry(tree, info["entry"], p, new_path, correct,
                                         r["first_beat_sec"], target, drift_ms)
                    changed += 1
                except Exception as ex:
                    print(f"     could not straighten ({ex}); left original alone")
            else:
                fixed_new_files.append((p, new_path))
                changed += 1

    # write outputs
    if apply and collection and tree is not None:
        outnml = os.path.join(os.path.dirname(os.path.expanduser(collection)) or ".",
                              "collection.beatgrid.nml")
        with open(outnml, "wb") as fh:
            fh.write(b'<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
            tree.write(fh, encoding="utf-8", xml_declaration=False)
        print(f"\nUpdated Traktor collection written: {outnml}")

    if fixed_new_files:
        delpath = os.path.join(out_dir, "delete-old-versions.command")
        _write_delete_script(fixed_new_files, delpath)
        print(f"Delete-old script (run AFTER listening): {delpath}")

    print(f"\n{'Applied' if apply else 'Would change'} {changed} tracks; "
          f"{len(fixed_new_files)} get a new fixed copy.")
    if not apply:
        print("This was a preview. Re-run with APPLY to make the changes.")
    return changed


def _make_fixed_copy(path, target_bpm, out_path, r, drift_ms):
    import tempfile
    if not bg._have("rubberband"):
        raise RuntimeError("rubberband is not installed. Run: brew install rubberband")
    sr_out = 44100
    y, sr = bg.decode_to_mono(path, bg.ANALYSIS_SR)
    duration = len(y) / sr
    oenv = bg.onset_envelope(y, sr)
    bpm, _ph = bg.estimate_tempo(oenv, sr, r["params"]["bpm_min"], r["params"]["bpm_max"])
    times, local = bg.local_tempo_curve(oenv, sr, bpm)
    if len(local) < 2:
        times, local = [0.0, duration], [bpm, bpm]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        src_wav = tf.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        warped = tf.name
    mapfile = warped + ".map.txt"
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path,
                        "-ar", str(sr_out), src_wav], check=True)
        import numpy as np
        pairs = bg.build_timemap_from_tempo(np.asarray(times), np.asarray(local),
                                            duration, sr_out, target_bpm)
        with open(mapfile, "w") as f:
            for s, t in pairs:
                f.write(f"{s} {t}\n")
        bg._run_rubberband(mapfile, pairs, src_wav, warped)
        _mux_tags(warped, path, out_path)
    finally:
        for q in (src_wav, warped, mapfile):
            try:
                os.remove(q)
            except OSError:
                pass


def _add_fixed_entry(tree, original_entry, original_path, new_path, correct_bpm,
                     first_beat_sec, target_bpm, drift_ms):
    """Clone the original Traktor entry for the new fixed file: same tags and
    cue points, corrected BPM + grid, cue times remapped through the warp."""
    import copy
    import numpy as np
    col = tree.getroot().find("COLLECTION")
    new_entry = copy.deepcopy(original_entry)
    # point LOCATION at the new file
    loc = new_entry.find("LOCATION")
    d = os.path.dirname(new_path)
    parts = os.path.normpath(d).strip("/").split("/")
    loc.set("DIR", "/:" + "/:".join(parts) + "/:")
    loc.set("FILE", os.path.basename(new_path))
    # corrected tempo + one grid marker
    tn.set_tempo(new_entry, target_bpm)
    # remap cue times (ms) through the warp so they still land on their moments
    y, sr = bg.decode_to_mono(original_path, bg.ANALYSIS_SR)
    dur = len(y) / sr
    oenv = bg.onset_envelope(y, sr)
    bpm, _ph = bg.estimate_tempo(oenv, sr, 70, 180)
    times, local = bg.local_tempo_curve(oenv, sr, bpm)
    if len(local) < 2:
        times, local = np.array([0.0, dur]), np.array([bpm, bpm])
    tt = np.asarray(times); ll = np.asarray(local)
    f = np.interp(np.arange(0, dur, 0.05), tt, ll, left=ll[0], right=ll[-1]) / 60.0
    grid_t = np.arange(0, dur, 0.05)
    beats = np.concatenate([[0.0], np.cumsum((f[:-1] + f[1:]) / 2 * np.diff(grid_t))])
    out_t = beats / (target_bpm / 60.0)

    def remap_ms(old_ms):
        old_s = old_ms / 1000.0
        return float(np.interp(old_s, grid_t, out_t)) * 1000.0

    for cue in new_entry.findall("CUE_V2"):
        if cue.get("TYPE") == "4":
            new_entry.remove(cue)                      # drop old grid marker
        else:
            try:
                cue.set("START", f"{remap_ms(float(cue.get('START'))):.6f}")
            except (TypeError, ValueError):
                pass
    tn.set_grid_marker(new_entry, remap_ms(first_beat_sec * 1000.0) / 1000.0)
    col.append(new_entry)


def _write_delete_script(pairs, path):
    lines = ["#!/bin/bash",
             "# Move the ORIGINAL (drifting) versions to the Trash, now that a",
             "# fixed copy sits next to each. Delete a line to KEEP that original.",
             "# Double-click this file, or run it in Terminal.", ""]
    for original, new in pairs:
        lines.append(f'# fixed copy: {new}')
        safe = original.replace('"', '\\"')
        lines.append(
            f'''osascript -e 'tell app "Finder" to delete POSIX file "{safe}"' '''
            f'&& echo "trashed: {os.path.basename(original)}"')
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    os.chmod(path, 0o755)


# ---------------------------------------------------------------------------
# Triage from the NML alone (no audio) - a quick "suspects" list. A round whole
# number BPM usually means Traktor never properly analysed the track, so those
# are the ones most likely to be off. Fractional BPMs were beat-analysed.
# ---------------------------------------------------------------------------
def triage(collection, out_dir):
    index, _ = index_collection(collection)
    rows = []
    for path, info in index.items():
        bpm = info["bpm"]
        if bpm is None:
            look = "NO BPM SET"
        elif abs(bpm - round(bpm)) < 0.001:
            look = "LIKELY OFF (round number)"
        else:
            look = "probably analysed"
        rows.append({"name": os.path.basename(path), "folder": os.path.dirname(path),
                     "path": path, "bpm": bpm, "look": look,
                     "cues": info["cues"]})
    rows.sort(key=lambda r: (r["look"] != "LIKELY OFF (round number)", r["name"].lower()))
    os.makedirs(out_dir, exist_ok=True)
    xlsx = os.path.join(out_dir, "beatgrid-suspects.xlsx")
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook(); ws = wb.active; ws.title = "suspects"
    ws.append(["#", "Track", "Traktor BPM", "Looks", "Your cue pts",
               "Folder", "Full path"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="404040")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for i, r in enumerate(rows, 1):
        ws.append([i, r["name"], r["bpm"], r["look"], r["cues"] or "",
                   r["folder"], r["path"]])
        if r["look"].startswith("LIKELY") or r["look"] == "NO BPM SET":
            ws.cell(row=i + 1, column=4).fill = PatternFill("solid", fgColor="FFC7CE")
    for j, w in enumerate([4, 46, 13, 26, 12, 30, 60], 1):
        ws.column_dimensions[ws.cell(row=1, column=j).column_letter].width = w
    ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
    wb.save(xlsx)
    likely = sum(1 for r in rows if r["look"].startswith("LIKELY") or r["look"] == "NO BPM SET")
    print(f"{len(rows)} tracks; {likely} look likely-off (round/blank BPM).")
    print(f"Suspects list: {xlsx}")
    return xlsx


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="organize", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "fix"):
        sp = sub.add_parser(name)
        sp.add_argument("folders", nargs="+")
        sp.add_argument("--collection", default=None)
        sp.add_argument("--out", default="output")
        sp.add_argument("--drift-ms", dest="drift_ms", type=float, default=25.0)
        if name == "fix":
            sp.add_argument("--apply", action="store_true")
            sp.add_argument("--warp", action="store_true",
                            help="also straighten drifting tracks into new files "
                                 "(default: just fix their BPM, no new file)")
    pt = sub.add_parser("triage")
    pt.add_argument("--collection", required=True)
    pt.add_argument("--out", default="output")

    args = p.parse_args(argv)
    if args.cmd == "scan":
        scan(args.folders, args.out, args.collection, args.drift_ms)
    elif args.cmd == "triage":
        triage(args.collection, args.out)
    else:
        fix(args.folders, args.out, args.collection, args.drift_ms, args.apply,
            getattr(args, "warp", False))


if __name__ == "__main__":
    main()
