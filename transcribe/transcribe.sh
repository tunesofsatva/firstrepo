#!/usr/bin/env bash
#
# One-command local video transcription for Apple Silicon (M-series) Macs.
#
# It looks at every video in the ./input folder and, for each one, produces:
#   ./output/<name>.txt   (plain text transcript)
#   ./output/<name>.srt   (subtitles with timestamps)
#
# Long videos (3.5-7 hours) are handled automatically: the audio is split into
# internal chunks (default 30 minutes), each chunk is transcribed on the GPU,
# and the results are stitched back together with correct timestamps. You never
# split anything by hand.
#
# Usage:
#   ./transcribe.sh
#
# Optional settings (advanced - safe to ignore):
#   MODEL=...          which Whisper model to use
#   LANGUAGE=en        force a language ("" or "auto" = auto-detect)
#   CHUNK_MINUTES=30   internal chunk length in minutes (0 = no chunking)
#
set -euo pipefail

# --- Resolve folders relative to this script, so it works from anywhere -------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"
WORK_DIR="$SCRIPT_DIR/.work"
VENV="$SCRIPT_DIR/.venv"

# --- Settings (override by exporting before running) --------------------------
MODEL="${MODEL:-mlx-community/whisper-large-v3-mlx}"
LANGUAGE="${LANGUAGE:-en}"
CHUNK_MINUTES="${CHUNK_MINUTES:-30}"
# "False" stops Whisper from getting stuck repeating a phrase during crowd
# noise / silence (common in sports & event audio). Set to "True" to restore
# the default behaviour.
CONDITION_ON_PREVIOUS="${CONDITION_ON_PREVIOUS:-False}"

mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$WORK_DIR"

# --- Sanity checks ------------------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg is not installed. Run ./setup.sh first." >&2
  exit 1
fi

if [ -f "$VENV/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

if ! command -v mlx_whisper >/dev/null 2>&1; then
  echo "ERROR: mlx_whisper is not installed. Run ./setup.sh first." >&2
  exit 1
fi

# --- Find videos --------------------------------------------------------------
shopt -s nullglob nocaseglob
# Accept both video and audio files (YouTube downloads arrive as audio).
videos=("$INPUT_DIR"/*.{mp4,mov,mkv,m4v,avi,webm,mpg,mpeg,ts,flv,m4a,mp3,aac,flac,ogg,opus,wav,wma})
shopt -u nullglob nocaseglob

if [ ${#videos[@]} -eq 0 ]; then
  echo "No videos or audio files found in: $INPUT_DIR"
  echo "Drop a file in that folder (or run ./download.sh) and try again."
  exit 0
fi

echo "=========================================================="
echo " Found ${#videos[@]} video(s) to transcribe"
echo " Model:        $MODEL"
echo " Language:     ${LANGUAGE:-auto-detect}"
echo " Chunk length: ${CHUNK_MINUTES} min (0 = whole file at once)"
echo "=========================================================="

# Build the --language argument only when a language is actually set.
lang_args=()
if [ -n "$LANGUAGE" ] && [ "$LANGUAGE" != "auto" ]; then
  lang_args=(--language "$LANGUAGE")
fi

transcribe_chunk() {  # $1 = audio file, $2 = output dir
  local audio="$1" outdir="$2"
  mkdir -p "$outdir"
  mlx_whisper "$audio" \
    --model "$MODEL" \
    ${lang_args[@]+"${lang_args[@]}"} \
    --condition-on-previous-text "$CONDITION_ON_PREVIOUS" \
    --output-dir "$outdir" \
    --output-format all
}

for video in "${videos[@]}"; do
  name="$(basename "$video")"
  stem="${name%.*}"
  final_txt="$OUTPUT_DIR/$stem.txt"
  final_srt="$OUTPUT_DIR/$stem.srt"
  final_md="$OUTPUT_DIR/$stem.md"

  echo
  echo "----------------------------------------------------------"
  echo " Video: $name"

  if [ "${FORCE:-0}" != "1" ] && [ -f "$final_txt" ] && [ -f "$final_srt" ]; then
    # Already transcribed. Make sure the Markdown version exists too.
    if [ ! -f "$final_md" ]; then
      python3 "$SCRIPT_DIR/srt_to_md.py" "$final_srt" "$stem" "$final_md"
    fi
    echo " Already done (found existing transcript). Skipping."
    echo " (Delete the files in ./output, or run FORCE=1 ./transcribe.sh, to re-run.)"
    continue
  fi

  vwork="$WORK_DIR/$stem"
  mkdir -p "$vwork"
  audio="$vwork/audio.wav"

  # 1) Extract a clean 16 kHz mono WAV (what Whisper expects) ------------------
  if [ ! -f "$audio" ]; then
    echo " Step 1/4: extracting audio..."
    ffmpeg -nostdin -y -i "$video" -vn -ac 1 -ar 16000 -c:a pcm_s16le \
      "$audio" >/dev/null 2>&1
  else
    echo " Step 1/4: audio already extracted, reusing."
  fi

  manifest="$vwork/manifest.txt"
  : > "$manifest"

  if [ "${SKIP_SILENCE:-0}" = "1" ]; then
    # 2) Detect speech regions and transcribe only those (skip silence/noise)--
    seg_file="$vwork/vad_segments.txt"
    segs_dir="$vwork/segs"
    out_dir="$vwork/out"
    mkdir -p "$segs_dir"
    seg_max=$(( (CHUNK_MINUTES > 0 ? CHUNK_MINUTES : 30) * 60 ))
    if [ ! -s "$seg_file" ]; then
      echo " Step 2/4: detecting speech (skipping silence & crowd noise)..."
      if ! python3 "$SCRIPT_DIR/vad_segments.py" "$audio" "$seg_max" > "$seg_file"; then
        rm -f "$seg_file"
        echo " ERROR: speech detection failed. Did you run 'INSTALL_VAD=1 ./setup.sh'?" >&2
        exit 1
      fi
    else
      echo " Step 2/4: speech regions already detected, reusing."
    fi

    # 3) Transcribe each speech region (resumable) ----------------------------
    total=$(wc -l < "$seg_file" | tr -d ' ')
    i=0
    while read -r start dur; do
      [ -z "$start" ] && continue
      i=$((i + 1))
      seg="$(printf '%s/seg_%03d.wav' "$segs_dir" "$i")"
      cbase="$(basename "${seg%.*}")"
      csrt="$out_dir/$cbase.srt"
      if [ ! -f "$csrt" ]; then
        echo " Step 3/4: transcribing speech region $i of $total ..."
        ffmpeg -nostdin -y -i "$audio" -ss "$start" -t "$dur" \
          -ac 1 -ar 16000 -c:a pcm_s16le "$seg" >/dev/null 2>&1
        transcribe_chunk "$seg" "$out_dir"
        rm -f "$seg"   # keep the transcript, drop the temporary audio
      else
        echo " Step 3/4: speech region $i of $total already done, reusing."
      fi
      # Offset = this region's real start time, so timestamps stay correct.
      printf '%s\t%s\n' "$csrt" "$start" >> "$manifest"
    done < "$seg_file"
  elif [ "$CHUNK_MINUTES" -gt 0 ]; then
    # 2) Split audio into fixed-length chunks ---------------------------------
    chunk_secs=$(( CHUNK_MINUTES * 60 ))
    chunks_dir="$vwork/chunks"
    mkdir -p "$chunks_dir"
    if ! ls "$chunks_dir"/chunk_*.wav >/dev/null 2>&1; then
      echo " Step 2/4: splitting into ${CHUNK_MINUTES}-minute chunks..."
      ffmpeg -nostdin -y -i "$audio" -f segment \
        -segment_time "$chunk_secs" -c copy \
        "$chunks_dir/chunk_%03d.wav" >/dev/null 2>&1
    else
      echo " Step 2/4: chunks already exist, reusing."
    fi

    # 3) Transcribe each chunk (resumable) ------------------------------------
    out_dir="$vwork/out"
    offset=0
    total=$(ls "$chunks_dir"/chunk_*.wav | wc -l | tr -d ' ')
    i=0
    for chunk in "$chunks_dir"/chunk_*.wav; do
      i=$((i + 1))
      cbase="$(basename "${chunk%.*}")"
      csrt="$out_dir/$cbase.srt"
      if [ ! -f "$csrt" ]; then
        echo " Step 3/4: transcribing chunk $i of $total ..."
        transcribe_chunk "$chunk" "$out_dir"
      else
        echo " Step 3/4: chunk $i of $total already transcribed, reusing."
      fi
      # Record this chunk's SRT plus its start offset (in seconds).
      printf '%s\t%s\n' "$csrt" "$offset" >> "$manifest"
      # Advance the offset by this chunk's real duration.
      dur=$(ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 "$chunk")
      offset=$(awk -v a="$offset" -v b="$dur" 'BEGIN{printf "%.3f", a + b}')
    done
  else
    # No chunking: transcribe the whole file in one pass ----------------------
    echo " Step 2/4: chunking disabled, transcribing whole file..."
    out_dir="$vwork/out"
    transcribe_chunk "$audio" "$out_dir"
    printf '%s\t%s\n' "$out_dir/audio.srt" "0" >> "$manifest"
    echo " Step 3/4: transcription complete."
  fi

  # 4) Stitch the pieces together --------------------------------------------
  echo " Step 4/4: assembling final transcript and subtitles..."
  python3 "$SCRIPT_DIR/merge_srt.py" "$manifest" "$final_srt"

  # Plain-text transcript: concatenate each chunk's .txt in order.
  : > "$final_txt"
  while IFS=$'\t' read -r srt_path _offset; do
    txt_path="${srt_path%.srt}.txt"
    if [ -f "$txt_path" ]; then
      cat "$txt_path" >> "$final_txt"
      printf '\n' >> "$final_txt"
    fi
  done < "$manifest"

  # Markdown transcript with timestamps (handy for analysis in Claude).
  python3 "$SCRIPT_DIR/srt_to_md.py" "$final_srt" "$stem" "$final_md"

  echo " DONE -> $final_txt"
  echo "      -> $final_srt"
  echo "      -> $final_md"
done

echo
echo "=========================================================="
echo " All done. Your transcripts are in: $OUTPUT_DIR"
echo "=========================================================="
