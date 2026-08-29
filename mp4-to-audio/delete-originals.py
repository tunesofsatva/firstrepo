#!/usr/bin/env python3
"""
delete-originals.py
-------------------
Safely delete the original .mp4/.wav files -- but ONLY the ones whose Traktor
cues/grid actually transferred to their new .m4a (i.e. relink succeeded for
them). This protects tracks that relink skipped as "ambiguous" or "no match":
their originals are KEPT so you don't orphan their cues.

It decides using the relink-log.csv that relink-collection.py wrote. A .mp4/.wav
is deleted only if:
  * its sibling .m4a exists and is non-empty, AND
  * that .m4a is listed in the relink log with a successful match
    (result = "folder+name" or "name-only").

REQUIRES: Python 3 (standard library only).

USAGE:
  # preview:
  python3 delete-originals.py --relink-log "<relink-log.csv>" --dry-run "folder1" ["folder2" ...]
  # delete for real:
  python3 delete-originals.py --relink-log "<relink-log.csv>" "folder1" ["folder2" ...]
"""
import argparse, csv, os, sys

SOURCE_EXTS = (".mp4", ".wav")

def die(msg, code=2):
    sys.stderr.write("Error: " + msg + "\n"); sys.exit(code)

def norm(p):
    return os.path.normcase(os.path.abspath(p))

def main():
    ap = argparse.ArgumentParser(description="Delete .mp4/.wav originals whose cues relinked to .m4a.")
    ap.add_argument("folder", nargs="+", help="One or more folders (recurses).")
    ap.add_argument("--relink-log", required=True, help="relink-log.csv written by relink-collection.py")
    ap.add_argument("--dry-run", action="store_true", help="Report only; delete nothing.")
    args = ap.parse_args()

    for fol in args.folder:
        if not os.path.isdir(fol): die("'%s' is not a folder." % fol)
    if not os.path.isfile(args.relink_log): die("relink log not found: %s" % args.relink_log)

    # Set of .m4a paths that relink successfully repointed.
    relinked = set()
    with open(args.relink_log, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("result") in ("folder+name", "name-only"):
                relinked.add(norm(row["m4a"]))
    print("relink log: %d tracks marked successfully relinked." % len(relinked))

    deleted = kept_notrelinked = kept_nom4a = 0
    for fol in args.folder:
        for dp, _, files in os.walk(fol):
            for f in files:
                if not f.lower().endswith(SOURCE_EXTS):
                    continue
                src = os.path.join(dp, f)
                stem = os.path.splitext(f)[0]
                m4a = os.path.join(dp, stem + ".m4a")
                if not (os.path.isfile(m4a) and os.path.getsize(m4a) > 0):
                    print("  [KEEP: no .m4a ] %s" % src); kept_nom4a += 1; continue
                if norm(m4a) not in relinked:
                    print("  [KEEP: not relinked] %s" % src); kept_notrelinked += 1; continue
                if args.dry_run:
                    print("  [would delete ] %s" % src); deleted += 1; continue
                os.remove(src)
                if not os.path.exists(src):
                    print("  [DELETED] %s" % src); deleted += 1
                else:
                    print("  [WARN: could not delete] %s" % src)

    print("\n===================== SUMMARY =====================")
    print("  %-24s: %d" % ("deleted" if not args.dry_run else "would delete", deleted))
    print("  kept (cues NOT relinked): %d   <-- handle these in Traktor, then delete manually" % kept_notrelinked)
    print("  kept (no .m4a yet)      : %d" % kept_nom4a)
    if kept_notrelinked:
        print("\n  The KEPT 'not relinked' files still have their cues in collection.nml")
        print("  under their original name. Nothing was lost -- deal with them later.")

if __name__ == "__main__":
    main()
