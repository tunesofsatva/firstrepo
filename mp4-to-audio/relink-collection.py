#!/usr/bin/env python3
"""
relink-collection.py
--------------------
Carry your Traktor CUE POINTS, LOOPS, BEATGRID (and every other field) over to
the converted files -- with ZERO manual redo.

How it works: your cues/loops/grid live inside each track's entry in
collection.nml. Traktor links an entry to a file by its NAME. When you convert
song.wav -> song.m4a, the entry still points at the old .wav. This tool rewrites
those entries to point at the new .m4a instead. Because it's the SAME entry,
ALL of its data -- cues, loops, beatgrid, BPM, key, rating, Comment 1/2, mix,
color, play count -- instantly belongs to the .m4a. Nothing is recreated; the
link is just repointed.

It writes a NEW collection file and NEVER touches your original. You then (with
Traktor CLOSED) back up your live collection.nml and swap in the new one.

MATCHING: each .m4a is matched to its entry by "<parent folder>/<filename stem>"
(fallback: filename stem). Only entries whose file currently ends in a source
extension (.wav .mp4 .aif .aiff .flac .mov .m4v .avi) are repointed.

CUE ALIGNMENT: cues are stored as time positions (ms). For LOSSLESS conversions
(WAV->ALAC, MP4 AAC stream-copy) the audio timing is identical, so every cue and
the grid line up exactly. Lossy re-encodes can shift by a few ms.

REQUIRES: Python 3 (standard library only).

USAGE:
    # Preview (writes nothing):
    python3 relink-collection.py --collection "/path/collection.nml" --dry-run "/music/folder"

    # Produce the relinked collection (default output: collection_RELINKED.nml):
    python3 relink-collection.py --collection "/path/collection.nml" "/music/folder"

THEN, in Traktor:
    1. Quit Traktor completely.
    2. Back up your live collection.nml.
    3. Replace it with the RELINKED file (rename it to collection.nml), or keep
       the original and load this one -- test on a COPY of your setup first.
    4. Open Traktor, load one .m4a, confirm cues/loops/grid are all there.
"""
import argparse, csv, os, sys, xml.etree.ElementTree as ET

SOURCE_EXTS = {".wav", ".mp4", ".aif", ".aiff", ".flac", ".mov", ".m4v", ".avi"}

def die(msg, code=2):
    sys.stderr.write("Error: " + msg + "\n"); sys.exit(code)

def stem_ext(fname):
    s, e = os.path.splitext(fname); return s, e.lower()

def parent_of(dir_attr):
    parts = [p for p in dir_attr.replace("/:", "/").split("/") if p]
    return parts[-1] if parts else ""

def build_index(root):
    by_tail, by_stem = {}, {}
    for entry in root.iter("ENTRY"):
        loc = entry.find("LOCATION")
        if loc is None: continue
        f = loc.get("FILE", "")
        if not f: continue
        stem, ext = stem_ext(f)
        rec = (entry, loc, f, ext)
        tail = (parent_of(loc.get("DIR","")) + "/" + stem).lower()
        by_tail.setdefault(tail, []).append(rec)
        by_stem.setdefault(stem.lower(), []).append(rec)
    return by_tail, by_stem

def find_entry(m4a_path, by_tail, by_stem):
    stem = os.path.splitext(os.path.basename(m4a_path))[0]
    parent = os.path.basename(os.path.dirname(m4a_path))
    tail = (parent + "/" + stem).lower()
    hits = by_tail.get(tail)
    if hits and len(hits) == 1: return hits[0], "folder+name"
    if hits and len(hits) > 1:  return None, "ambiguous"
    hits = by_stem.get(stem.lower())
    if hits and len(hits) == 1: return hits[0], "name-only"
    if hits and len(hits) > 1:  return None, "ambiguous"
    return None, "no-match"

def cue_summary(entry):
    cues = entry.findall("CUE_V2")
    grid = sum(1 for c in cues if c.get("TYPE") == "4")
    loops = sum(1 for c in cues if _f(c.get("LEN")) > 0)
    hot = sum(1 for c in cues if c.get("TYPE") != "4" and _f(c.get("LEN")) == 0)
    return len(cues), grid, hot, loops

def _f(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0

def main():
    ap = argparse.ArgumentParser(description="Repoint Traktor collection.nml entries to converted .m4a files (keeps cues/loops/grid).")
    ap.add_argument("folder", nargs="+", help="One or more folders of converted .m4a files (recurses).")
    ap.add_argument("--collection", required=True, help="Path to Traktor collection.nml (input; never modified).")
    ap.add_argument("--out", default=None, help="Output path (default: collection_RELINKED.nml beside the input).")
    ap.add_argument("--dry-run", action="store_true", help="Report only; write no output file.")
    ap.add_argument("--log", default=None, help="CSV log path (default: <folder>/relink-log.csv).")
    args = ap.parse_args()

    for fol in args.folder:
        if not os.path.isdir(fol): die("'%s' is not a folder." % fol)
    if not os.path.isfile(args.collection): die("collection not found: %s" % args.collection)
    out_path = args.out or os.path.join(os.path.dirname(os.path.abspath(args.collection)),
                                         "collection_RELINKED.nml")
    if os.path.abspath(out_path) == os.path.abspath(args.collection):
        die("output must differ from the input collection (never overwrite the original).")

    try:
        tree = ET.parse(args.collection)
    except Exception as e:
        die("could not parse collection.nml: %s" % e)
    root = tree.getroot()
    by_tail, by_stem = build_index(root)

    m4as = []
    for fol in args.folder:
        for dp, _, files in os.walk(fol):
            for f in files:
                if f.lower().endswith(".m4a"):
                    m4as.append(os.path.join(dp, f))
    m4as = sorted(set(m4as))
    print("Found %d .m4a files under %d folder(s):" % (len(m4as), len(args.folder)))
    for fol in args.folder: print("   " + fol)
    print()

    relinked = skipped_already = ambiguous = nomatch = notsource = 0
    tot_cues = tot_grid = tot_loops = 0
    rows = []
    seen_entries = set()
    for p in m4as:
        rec, how = find_entry(p, by_tail, by_stem)
        base = os.path.basename(p)
        if rec is None:
            if how == "ambiguous": ambiguous += 1
            else: nomatch += 1
            print("  [%-11s] %s" % (how, base))
            rows.append({"m4a": p, "result": how, "old_file": "", "cues": "", "grid": "", "loops": ""})
            continue
        entry, loc, oldf, ext = rec
        if id(entry) in seen_entries:
            print("  [dup-target ] %s (an entry was already repointed to this name)" % base)
            rows.append({"m4a": p, "result": "dup-target", "old_file": oldf, "cues":"","grid":"","loops":""})
            continue
        if ext == ".m4a":
            skipped_already += 1
            continue
        if ext not in SOURCE_EXTS:
            notsource += 1
            print("  [not-source ] %s (matched entry is %s, not a converted type)" % (base, ext))
            rows.append({"m4a": p, "result": "not-source(%s)"%ext, "old_file": oldf, "cues":"","grid":"","loops":""})
            continue
        ncues, grid, hot, loops = cue_summary(entry)
        newf = os.path.splitext(oldf)[0] + ".m4a"
        if not args.dry_run:
            loc.set("FILE", newf)          # THE repoint: same entry, new filename
            loc.set("VOLUMEID", loc.get("VOLUMEID", ""))
        seen_entries.add(id(entry))
        relinked += 1
        tot_cues += ncues; tot_grid += grid; tot_loops += loops
        print("  [RELINK] %s  (cues=%d grid=%d loops=%d)  %s -> %s" %
              (base, ncues, grid, loops, ext, ".m4a"))
        rows.append({"m4a": p, "result": how, "old_file": oldf,
                     "cues": ncues, "grid": grid, "loops": loops})

    if not args.dry_run and relinked:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
                tree.write(f, encoding="unicode", xml_declaration=False,
                           short_empty_elements=False)
            out_note = "WROTE relinked collection: %s" % out_path
        except Exception as e:
            out_note = "!! could not write output: %s" % e
    elif args.dry_run:
        out_note = "(dry-run: no file written)"
    else:
        out_note = "(nothing to relink; no file written)"

    log_path = args.log or os.path.join(args.folder[0], "relink-log.csv")
    try:
        with open(log_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["m4a","result","old_file","cues","grid","loops"])
            w.writeheader(); w.writerows(rows)
        log_note = "log: %s" % log_path
    except Exception as e:
        log_note = "(could not write log: %s)" % e

    print("\n===================== SUMMARY =====================")
    print("  .m4a files            : %d" % len(m4as))
    print("  %-21s: %d" % ("relinked" if not args.dry_run else "would relink", relinked))
    print("    carrying cues       : %d total across those tracks" % tot_cues)
    print("    carrying grid marks : %d" % tot_grid)
    print("    carrying loops      : %d" % tot_loops)
    print("  already .m4a (skipped): %d" % skipped_already)
    print("  ambiguous (skipped)   : %d" % ambiguous)
    print("  no match (skipped)    : %d" % nomatch)
    if notsource: print("  non-source (skipped)  : %d" % notsource)
    print("  " + out_note)
    print("  " + log_note)
    print("\n  NEXT: quit Traktor, back up your live collection.nml, then swap in")
    print("  the RELINKED file. Test one track first -- cues/loops/grid should")
    print("  all be present on the .m4a.")

if __name__ == "__main__":
    main()
