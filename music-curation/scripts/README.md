# Sangeet dance curation scripts

Builds a category-wise dance playlist workbook from a Traktor `collection.nml`.
Run from this folder, in order:

    python3 parse2.py /path/to/collection.nml   # -> tracks.json (tracks + playlist membership)
    python3 build.py                            # -> cats.json (language/era buckets, drop rules)
    python3 final.py                            # -> final.json (clean names, renames/drops from overrides.py)
    python3 write_xlsx.py "out.xlsx"

`overrides.py` holds the hand-curated renames, drops and category moves.
