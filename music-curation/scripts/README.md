# Sangeet dance curation scripts

Builds a category-wise dance playlist workbook from a Traktor `collection.nml`.
Run from this folder, in order:

    python3 parse2.py /path/to/collection.nml   # -> tracks.json (tracks + playlist membership)
    python3 build.py                            # -> cats.json (language/era buckets, drop rules)
    python3 final.py                            # -> final.json (clean names, renames/drops from overrides.py)
    python3 stage2.py                           # -> final2.json (mashups -> first song, re-home by language,
                                                #    dedupe, popularity cut via popular.json)
    python3 write_xlsx.py "out.xlsx" final2.json

`overrides.py` holds the hand-curated renames, drops and category moves.
`popular.json` lists the songs kept for Tamil, Kannada and Malayalam (roughly the most popular half).
