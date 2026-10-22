#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Ableton Live 12 MCP Video & Animated GIF Showcase Asset Generator
# Generates:
#   - assets/demo_overview.mp4 (1280x720 H.264/AAC with synchronized visualizers)
#   - assets/demo_overview.gif (480x270 palette-optimized looping animated GIF)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

WAV_FILE="${ROOT_DIR}/assets/showcase_demo.wav"
MP4_FILE="${ROOT_DIR}/assets/demo_overview.mp4"
GIF_FILE="${ROOT_DIR}/assets/demo_overview.gif"

if [[ ! -f "${WAV_FILE}" ]]; then
  echo "Error: ${WAV_FILE} not found. Running generate_showcase_audio.py first..."
  python3 "${ROOT_DIR}/scripts/generate_showcase_audio.py"
fi

mkdir -p "${ROOT_DIR}/assets"

echo "==> Rendering ${MP4_FILE} via ffmpeg (1280x720 H.264/AAC)..."
ffmpeg -y -i "${WAV_FILE}" -filter_complex \
  "[0:a]showwaves=s=1200x260:mode=line:colors=0x00d2ff[waves]; \
   [0:a]showspectrum=s=1200x260:mode=combined:color=magma:scale=log:saturation=3[spec]; \
   color=c=0x07080a:s=1280x720:d=15.48[bg]; \
   [bg][waves]overlay=40:90[bg1]; \
   [bg1][spec]overlay=40:390[v]" \
  -map "[v]" -map 0:a \
  -c:v libx264 -pix_fmt yuv420p -preset fast -crf 20 \
  -c:a aac -b:a 192k \
  "${MP4_FILE}"

echo "==> Rendering ${GIF_FILE} via ffmpeg (480x270 palette-optimized loop)..."
ffmpeg -y -i "${MP4_FILE}" -t 4.0 -vf \
  "fps=12,scale=480:270:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer" \
  "${GIF_FILE}"

echo "==> Media Generation Complete:"
ls -lh "${MP4_FILE}" "${GIF_FILE}"

echo "==> Verifying generated media via ffprobe:"
ffprobe -hide_banner "${MP4_FILE}"
ffprobe -hide_banner "${GIF_FILE}"

echo "==> Video and GIF asset generation succeeded."
