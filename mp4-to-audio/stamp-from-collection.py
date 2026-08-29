#!/usr/bin/env python3
"""
stamp-from-collection.py
------------------------
Write the metadata you curated in Traktor (Rating, Comment 1, Comment 2, Mix,
Genre, Key, BPM, Artist, Album, Remixer, Label) from Traktor's collection.nml
DIRECTLY into your converted .m4a files -- so it becomes permanent in the file,
independent of whether Traktor ever wrote tags to the originals.

It matches each .m4a to its Traktor entry by "<parent folder>/<filename stem>"
(falling back to just the filename stem), so a track keeps its data as long as
its name and folder are unchanged. It only ADDS/OVERWRITES the fields below --
it never blanks other tags. Cue points/beatgrids are NOT written (Traktor keeps
those only in collection.nml; that file stays your cue backup).

Field mapping (Traktor collection.nml  ->  .m4a tag):
    TITLE                 -> title            (©nam)
    ARTIST                -> artist           (©ART)
    ALBUM TITLE           -> album            (©alb)
    INFO GENRE            -> genre            (©gen)
    INFO COMMENT          -> comment          (©cmt)          [Comment 1]
    TEMPO BPM             -> bpm              (tmpo)
    INFO RANKING (÷51)    -> RATING_STARS 0-5 (freeform)      [star rating]
    INFO RATING           -> COMMENT2         (freeform)      [Comment 2 text]
    INFO MIX              -> MIX              (freeform)
    INFO KEY              -> INITIALKEY       (freeform)
    INFO REMIXER          -> REMIXER          (freeform)
    INFO LABEL            -> LABEL            (freeform)
Freeform tags are stored under the "com.apple.iTunes:" namespace and are read
back by exiftool, mutagen, MediaMonkey, etc.

REQUIRES: pip3 install mutagen   (Python 3)

USAGE:
    # Preview matches only (writes nothing):
    python3 stamp-from-collection.py --collection "/path/collection.nml" --dry-run "/music/folder"

    # Stamp for real:
    python3 stamp-from-collection.py --collection "/path/collection.nml" "/music/folder"

A CSV record of everything written is saved as stamp-log.csv in the target
folder (override with --log).
"""
import argparse, csv, os, sys, xml.etree.ElementTree as ET

def die(msg, code=2):
    sys.stderr.write("Error: " + msg + "\n"); sys.exit(code)

try:
    from mutagen.mp4 import MP4, MP4FreeForm
except ImportError:
    die("mutagen is not installed. Run:  pip3 install mutagen", 3)

FREEFORM_NS = "com.apple.iTunes"

def ff(name, value):
    """Build a freeform MP4 atom key + UTF-8 value."""
    key = "----:%s:%s" % (FREEFORM_NS, name)
    return key, [MP4FreeForm(str(value).encode("utf-8"))]

def stem_of(fname):
    return os.path.splitext(fname)[0]

def parse_collection(path):
    """Return two dicts: by 'parentdir/stem' (lower) and by 'stem' (lower).
    Each maps to a metadata dict. Ambiguous stems map to None (skip later)."""
    try:
        tree = ET.parse(path)
    except Exception as e:
        die("could not parse collection.nml: %s" % e)
    root = tree.getroot()
    by_tail, by_stem = {}, {}
    n = 0
    for entry in root.iter("ENTRY"):
        loc = entry.find("LOCATION")
        if loc is None:
            continue
        fname = loc.get("FILE", "")
        if not fname:
            continue
        dir_attr = loc.get("DIR", "")
        # Traktor uses "/:" as its path separator.
        parts = [p for p in dir_attr.replace("/:", "/").split("/") if p]
        parent = parts[-1] if parts else ""
        stem = stem_of(fname)

        info = entry.find("INFO")
        info = info if info is not None else ET.Element("INFO")
        album = entry.find("ALBUM")
        tempo = entry.find("TEMPO")

        meta = {}
        if entry.get("TITLE"):  meta["title"]  = entry.get("TITLE")
        if entry.get("ARTIST"): meta["artist"] = entry.get("ARTIST")
        if album is not None and album.get("TITLE"): meta["album"] = album.get("TITLE")
        if info.get("GENRE"):   meta["genre"]   = info.get("GENRE")
        if info.get("COMMENT"): meta["comment"] = info.get("COMMENT")   # Comment 1
        if info.get("RATING"):  meta["comment2"] = info.get("RATING")   # Comment 2
        if info.get("MIX"):     meta["mix"]     = info.get("MIX")
        if info.get("KEY"):     meta["key"]     = info.get("KEY")
        if info.get("REMIXER"): meta["remixer"] = info.get("REMIXER")
        if info.get("LABEL"):   meta["label"]   = info.get("LABEL")
        rk = info.get("RANKING")
        if rk and rk.isdigit():
            meta["stars"] = str(int(round(int(rk) / 51.0)))            # 0..5
        if tempo is not None and tempo.get("BPM"):
            try: meta["bpm"] = int(round(float(tempo.get("BPM"))))
            except ValueError: pass

        if not meta:
            continue
        n += 1
        tail = (parent + "/" + stem).lower()
        by_tail.setdefault(tail, meta)          # first wins; tails are usually unique
        sk = stem.lower()
        if sk in by_stem and by_stem[sk] != meta:
            by_stem[sk] = None                  # ambiguous stem -> don't trust it
        elif sk not in by_stem:
            by_stem[sk] = meta
    return by_tail, by_stem, n

def match(m4a_path, by_tail, by_stem):
    stem = stem_of(os.path.basename(m4a_path))
    parent = os.path.basename(os.path.dirname(m4a_path))
    tail = (parent + "/" + stem).lower()
    if tail in by_tail:
        return by_tail[tail], "folder+name"
    m = by_stem.get(stem.lower())
    if m:
        return m, "name-only"
    if stem.lower() in by_stem and by_stem[stem.lower()] is None:
        return None, "ambiguous"
    return None, "no-match"

def apply_tags(m4a_path, meta):
    audio = MP4(m4a_path)
    if "title" in meta:   audio["\xa9nam"] = [meta["title"]]
    if "artist" in meta:  audio["\xa9ART"] = [meta["artist"]]
    if "album" in meta:   audio["\xa9alb"] = [meta["album"]]
    if "genre" in meta:   audio["\xa9gen"] = [meta["genre"]]
    if "comment" in meta: audio["\xa9cmt"] = [meta["comment"]]
    if "bpm" in meta:     audio["tmpo"]    = [meta["bpm"]]
    for name, mkey in (("comment2","COMMENT2"),("mix","MIX"),("key","INITIALKEY"),
                       ("remixer","REMIXER"),("label","LABEL"),("stars","RATING_STARS")):
        if name in meta:
            k, v = ff(mkey, meta[name]); audio[k] = v
    audio.save()

def main():
    ap = argparse.ArgumentParser(description="Stamp Traktor collection.nml metadata into .m4a files.")
    ap.add_argument("folder", help="Folder of converted .m4a files (recurses).")
    ap.add_argument("--collection", required=True, help="Path to Traktor collection.nml")
    ap.add_argument("--dry-run", action="store_true", help="Show matches, write nothing.")
    ap.add_argument("--log", default=None, help="CSV log path (default: <folder>/stamp-log.csv)")
    args = ap.parse_args()

    if not os.path.isdir(args.folder): die("'%s' is not a folder." % args.folder)
    if not os.path.isfile(args.collection): die("collection not found: %s" % args.collection)

    by_tail, by_stem, n = parse_collection(args.collection)
    print("Loaded %d Traktor entries with metadata." % n)

    m4as = []
    for dirpath, _, files in os.walk(args.folder):
        for f in files:
            if f.lower().endswith(".m4a"):
                m4as.append(os.path.join(dirpath, f))
    m4as.sort()
    print("Found %d .m4a files under: %s\n" % (len(m4as), args.folder))

    log_path = args.log or os.path.join(args.folder, "stamp-log.csv")
    stamped = ambiguous = nomatch = 0
    rows = []
    for p in m4as:
        meta, how = match(p, by_tail, by_stem)
        if meta is None:
            if how == "ambiguous": ambiguous += 1
            else: nomatch += 1
            print("  [%-9s] %s" % (how, p))
            rows.append({"file": p, "match": how, "stars": "", "comment2": ""})
            continue
        fields = ",".join(sorted(meta.keys()))
        print("  [MATCH %-11s] %s" % (how, os.path.basename(p)))
        print("      -> %s" % fields)
        if not args.dry_run:
            try:
                apply_tags(p, meta); stamped += 1
            except Exception as e:
                print("      !! write failed: %s" % e)
                rows.append({"file": p, "match": "write-error", "stars": "", "comment2": ""})
                continue
        rows.append({"file": p, "match": how,
                     "stars": meta.get("stars",""), "comment2": meta.get("comment2","")})

    try:
        with open(log_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["file","match","stars","comment2"])
            w.writeheader(); w.writerows(rows)
        log_note = "log: %s" % log_path
    except Exception as e:
        log_note = "(could not write log: %s)" % e

    print("\n================= SUMMARY =================")
    print("  .m4a files          : %d" % len(m4as))
    print("  %-19s : %d" % ("stamped" if not args.dry_run else "would stamp",
                            (stamped if not args.dry_run else len(m4as)-ambiguous-nomatch)))
    print("  ambiguous (skipped) : %d" % ambiguous)
    print("  no match (skipped)  : %d" % nomatch)
    print("  " + log_note)
    print("  NOTE: cue points/beatgrids are NOT written to files -- keep your")
    print("        collection.nml backup as the cue safety net.")

if __name__ == "__main__":
    main()
