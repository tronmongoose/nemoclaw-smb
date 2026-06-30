#!/usr/bin/env bash
# Assemble narrated slides into the final film.
# MUST run under bash (not zsh) — array indexing differs. Invoke: `bash assemble.sh`.
# Env: FILM_WORK = scratch dir holding scenes/*.png, aud/s*.wav, title.png, end.png
#      FILM_OUT  = output mp4 path (e.g. demo/nemoclaw-pm-narrated.mp4)
set -e
WORK="${FILM_WORK:-/tmp/nemo-film}"
OUT="${FILM_OUT:-$WORK/film.mp4}"
cd "$WORK"

# One slide per scene; clip length = its narration. Order must match gen_kokoro.py.
imgs=(title.png scenes/turnover.png scenes/stall.png scenes/schedule.png scenes/performance.png scenes/portfolio.png scenes/agents.png scenes/owner.png scenes/swarm_caps.png scenes/swarm_market.png end.png)

: > list.txt
for i in "${!imgs[@]}"; do
  a="aud/s${i}.wav"
  d=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$a")
  D=$(awk -v x="$d" 'BEGIN{printf "%.2f", x+0.55}')
  ffmpeg -y -loglevel error -loop 1 -i "${imgs[$i]}" -i "$a" -t "$D" -r 30 \
    -vf "scale=1440:900,fade=t=in:st=0:d=0.35,format=yuv420p" \
    -af apad -c:v libx264 -crf 20 -preset medium -c:a aac -ar 44100 -ac 2 -pix_fmt yuv420p "clip_${i}.mp4"
  echo "clip ${i}  ${D}s  :: ${imgs[$i]}"
  echo "file 'clip_${i}.mp4'" >> list.txt
done

ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -c copy "$OUT"
echo "FINAL -> $OUT"
ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,codec_name -of default=nw=1 "$OUT"
