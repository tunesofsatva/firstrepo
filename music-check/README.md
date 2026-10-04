# Music download check (for your Mac)

Finds out which songs in your Shazam master Excel are already downloaded on
your MacBook, and which you still need to get.

It adds two columns to the `Shazam Master` sheet (saved as a **new copy**, your
original Excel is never changed):

| Column | Values |
|---|---|
| **Available on Mac?** | `Yes` (found), `No` (still to download), `Check` (a similar file was found) |
| **Download Comments** | the file that matched and its folder, or up to 3 similar files to verify by hand |

A `Download Check` sheet gives the totals.

Matching ignores capitals, punctuation and spacing, and treats common
Hindi/English spellings as the same word: `Yeh Dosti` = `Ye Dosti` = `YehDosti`,
`Deewana` = `Diwana`, `Pyaar` = `Pyar`, `Bairan` = `Bairaan`. It reads each
file's name and, if present, the title/artist tags inside the file.

- **Yes**: the song title matches and the artist is in the file name or tags.
  Long titles (3+ words) count without the artist.
- **Check**: the title is close but not certain. Examples: a different spelling
  (`Chor Bazari` vs `Chor Bazaare`), the same title by a different artist, or
  no artist in the file name. Open `Download Comments` and decide.
- **No**: nothing similar was found.

---

## Run it

1. Open **Terminal** (`Cmd + Space`, type "Terminal", press Enter).
2. Go to the `music-check` folder (inside your `firstrepo` folder) and run it
   with your master Excel:

   ```bash
   cd ~/firstrepo/music-check
   chmod +x run.sh
   ./run.sh ~/Downloads/Shazam_Master_Jan-Oct_2026.xlsx
   ```

   This scans your whole home folder (skipping `~/Library`) plus any plugged-in
   external drives. To scan only certain folders, list them after the Excel:

   ```bash
   ./run.sh ~/Downloads/Shazam_Master_Jan-Oct_2026.xlsx ~/Music ~/Downloads "/Volumes/DJ Drive"
   ```

3. macOS may ask whether Terminal can access Desktop, Documents, Downloads or
   external drives. Click **Allow**, or those folders can't be checked.

The result is saved next to your Excel as
`Shazam_Master_Jan-Oct_2026_with_downloads.xlsx`.

The first run spends about a minute setting up. Later runs take seconds.

## Prefer Claude to do the matching?

Run this one command. It only lists your music file names and saves the list to
your Desktop:

```bash
find ~ /Volumes -type f \( -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.wav' -o -iname '*.flac' -o -iname '*.aiff' -o -iname '*.aif' -o -iname '*.aac' -o -iname '*.ogg' -o -iname '*.opus' \) -not -path '*/Library/*' -not -name '._*' 2>/dev/null > ~/Desktop/music_files.txt
```

Upload `music_files.txt` to Claude together with the master Excel. Claude runs
the same check with:

```bash
python3 check_downloads.py Shazam_Master.xlsx --list music_files.txt
```
