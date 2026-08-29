#!/usr/bin/env python3
"""
traktor_nml - read a Traktor collection.nml, and for every track that beatgrid
can analyse, write back the exact BPM and a single grid marker on the true
downbeat. Fixes a whole library at once instead of retyping BPMs by hand.

SAFETY MODEL (this touches your Traktor collection, so it is deliberately timid)
-------------------------------------------------------------------------------
  * Dry-run by default: it only PRINTS what it would change. Nothing is written
    until you pass --apply.
  * Even with --apply it writes to a NEW file (collection.beatgrid.nml) next to
    the original. Your real collection.nml is never modified in place unless you
    additionally pass --in-place, and even then a timestamped .bak is made first.
  * It only ever changes two things per track: the <TEMPO> BPM and one grid
    marker (<CUE_V2 TYPE="4">). It never moves, repaths, or deletes tracks, and
    never touches your hotcues, loops, or anything else.
  * Quit Traktor before applying - Traktor rewrites collection.nml when it
    exits and would clobber the changes.

TWO FORMAT DETAILS TO CONFIRM AGAINST A REAL FILE (see verify_against_sample):
  1. LOCATION path encoding (VOLUME + DIR with '/:' separators).
  2. The unit of CUE_V2 START (this code assumes milliseconds).
Run  `python3 beatgrid.py nml --collection <file> --check`  to have it print how
it decoded your entries so we can confirm both before any --apply.
"""

import os
import shutil
import time
import xml.etree.ElementTree as ET

GRID_MARKER_TYPE = "4"          # Traktor CUE_V2 TYPE for a beatgrid marker


# ---------------------------------------------------------------------------
# LOCATION <-> filesystem path
# ---------------------------------------------------------------------------
def location_to_path(loc):
    """Reconstruct a filesystem path from a Traktor <LOCATION> element.

    Traktor stores e.g.
        DIR="/:Users/:satva/:Music/:Tracks/:"  FILE="Track.mp3"
        VOLUME="Macintosh HD"
    On the boot volume the real path is just DIR+FILE from '/'. On an external
    drive it is /Volumes/<VOLUME>/DIR+FILE. We try boot first, then external,
    and return whichever exists (or the boot guess if neither does).
    """
    d = loc.get("DIR", "") or ""
    f = loc.get("FILE", "") or ""
    vol = loc.get("VOLUME", "") or ""
    parts = [p for p in d.split("/:")]
    dir_posix = "/".join(parts)
    if not dir_posix.startswith("/"):
        dir_posix = "/" + dir_posix
    if not dir_posix.endswith("/"):
        dir_posix += "/"
    boot = dir_posix + f
    if os.path.exists(boot):
        return boot
    if vol:
        ext = "/Volumes/" + vol + dir_posix + f
        if os.path.exists(ext):
            return ext
    return boot


# ---------------------------------------------------------------------------
# Editing one ENTRY
# ---------------------------------------------------------------------------
def set_tempo(entry, bpm):
    tempo = entry.find("TEMPO")
    if tempo is None:
        tempo = ET.SubElement(entry, "TEMPO")
    tempo.set("BPM", f"{bpm:.6f}")
    if tempo.get("BPM_QUALITY") is None:
        tempo.set("BPM_QUALITY", "100.000000")


def set_grid_marker(entry, first_beat_sec):
    """Replace any existing grid markers with a single one at first_beat_sec.

    START is written in milliseconds (see the format-detail note at top).
    """
    for cue in list(entry.findall("CUE_V2")):
        if cue.get("TYPE") == GRID_MARKER_TYPE:
            entry.remove(cue)
    start_ms = first_beat_sec * 1000.0
    ET.SubElement(entry, "CUE_V2", {
        "NAME": "beatgrid",
        "DISPL_ORDER": "0",
        "TYPE": GRID_MARKER_TYPE,
        "START": f"{start_ms:.6f}",
        "LEN": "0.000000",
        "REPEATS": "-1",
        "HOTCUE": "-1",
    })


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def process(collection_path, analyze_fn, apply=False, in_place=False,
            check=False, only_under=None, drift="warp", warp_fn=None,
            out_dir="output", bpm_min=70.0, bpm_max=180.0, drift_ms=25.0,
            limit=None):
    """Walk the collection, analyse matched tracks, and (optionally) write.

    analyze_fn(path, bpm_min, bpm_max, drift_ms) -> analysis dict (beatgrid).
    warp_fn(path, target_bpm, out_path, ...) used for drifting tracks.
    """
    tree = ET.parse(collection_path)
    root = tree.getroot()
    collection = root.find("COLLECTION")
    if collection is None:
        raise RuntimeError("No <COLLECTION> found - is this a Traktor nml?")

    entries = collection.findall("ENTRY")
    print(f"Collection: {collection_path}")
    print(f"Entries in collection: {len(entries)}")

    matched = changed = drifting = missing = 0
    processed = 0
    for entry in entries:
        loc = entry.find("LOCATION")
        if loc is None:
            continue
        path = location_to_path(loc)
        exists = os.path.exists(path)
        if only_under and (not path.startswith(os.path.abspath(only_under))):
            continue
        if not exists:
            missing += 1
            if check:
                print(f"  MISSING  {path}")
            continue
        matched += 1

        if check:
            # Just show how we decoded this entry; don't analyse.
            tempo = entry.find("TEMPO")
            cur = tempo.get("BPM") if tempo is not None else "-"
            print(f"  OK  cur_bpm={cur:>10}  {path}")
            if limit and matched >= limit:
                break
            continue

        try:
            r = analyze_fn(path, bpm_min, bpm_max, drift_ms)
        except Exception as e:
            print(f"  SKIP (analyse error) {os.path.basename(path)}: {e}")
            continue
        if "error" in r:
            print(f"  SKIP {os.path.basename(path)}: {r['error']}")
            continue
        processed += 1

        if r["verdict"] == "drifting":
            drifting += 1
            note = ""
            if drift == "warp" and warp_fn is not None:
                base = os.path.splitext(os.path.basename(path))[0]
                target = float(r["bpm_rounded"])
                out_path = os.path.join(out_dir, f"{base} [{target:g} warped].wav")
                try:
                    os.makedirs(out_dir, exist_ok=True)
                    warp_fn(path, target, out_path, bpm_min, bpm_max)
                    note = f"  -> warped copy: {out_path} (import this)"
                except Exception as e:
                    note = f"  -> warp failed ({e}); left BPM/grid as best-fit"
            print(f"  DRIFT {r['bpm']:.3f} BPM  {os.path.basename(path)}{note}")

        # For constant tracks (and as a best-fit for drifting) write BPM + grid.
        if apply:
            set_tempo(entry, r["bpm"])
            set_grid_marker(entry, r["first_beat_sec"])
        changed += 1
        tag = "SET " if apply else "would set"
        print(f"  {tag} {r['bpm']:.3f} BPM, grid @ {r['first_beat_mmss']}"
              f"   {os.path.basename(path)}")
        if limit and processed >= limit:
            break

    print(f"\nMatched on disk: {matched}   analysed: {processed}   "
          f"drifting: {drifting}   missing files: {missing}")

    if check:
        print("\n--check only: nothing analysed or written. Confirm the paths "
              "above look right, then re-run without --check.")
        return

    if not apply:
        print("\nDRY RUN: nothing written. Re-run with --apply to write "
              "collection.beatgrid.nml (Traktor must be quit first).")
        return

    # write
    if in_place:
        bak = collection_path + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(collection_path, bak)
        out = collection_path
        print(f"\nBackup written: {bak}")
    else:
        out = os.path.join(os.path.dirname(collection_path) or ".",
                           "collection.beatgrid.nml")
    tree.write(out, encoding="utf-8", xml_declaration=True)
    print(f"Wrote: {out}")
    if not in_place:
        print("Quit Traktor, back up your real collection.nml, then replace it "
              "with this file (or import it) to apply the changes.")
