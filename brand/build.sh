#!/bin/bash
# Rebuild the $0 procedural brand kit (deterministic, ffmpeg only).
# sting: 3-tone rise, whoosh: filtered noise sweep, bed: low 2-tone loop.
set -e
cd "$(dirname "$0")"
ffmpeg -y -v error -f lavfi -i "sine=frequency=220:duration=0.6" \
  -f lavfi -i "sine=frequency=330:duration=0.6" \
  -f lavfi -i "sine=frequency=440:duration=0.9" \
  -filter_complex "[0:a][1:a][2:a]amix=inputs=3:duration=longest,afade=t=out:st=0.7:d=0.5,volume=0.5" sting.wav
ffmpeg -y -v error -f lavfi -i "anoisesrc=color=pink:duration=1.2:seed=7" \
  -filter_complex "highpass=f=400,lowpass=f=6000,afade=t=in:st=0:d=0.5,afade=t=out:st=0.7:d=0.5,volume=0.4" whoosh.wav
ffmpeg -y -v error -f lavfi -i "sine=frequency=110:duration=8" \
  -f lavfi -i "sine=frequency=165:duration=8" \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest,volume=0.12,aloop=loop=-1:size=352800" -t 8 bed.wav
echo "brand kit ready: sting.wav whoosh.wav bed.wav"
