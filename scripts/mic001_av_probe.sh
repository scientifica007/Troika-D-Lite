#!/usr/bin/env bash
set -euo pipefail

DURATION_SECONDS="${1:-90}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${2:-$ROOT_DIR/benchmark-results/mic001-av-$STAMP}"
OUT_FILE="$OUT_DIR/synthetic-video-plus-mic.mp4"
LOG_FILE="$OUT_DIR/synthetic-video-plus-mic.log"

for cmd in pactl gst-launch-1.0 timeout; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Required command not found: $cmd" >&2
    exit 1
  }
done

MIC="${TROIKA_D_LITE_MIC_SOURCE:-$(pactl get-default-source 2>/dev/null || true)}"
if [[ -z "$MIC" ]]; then
  MIC="$(pactl info | sed -n 's/^Default Source: //p' | head -n1)"
fi
if [[ -z "$MIC" || "$MIC" == *.monitor ]]; then
  echo "Could not determine a usable microphone source: $MIC" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "MIC-001 synthetic A/V probe"
echo "Microphone: $MIC"
echo "Duration: ${DURATION_SECONDS}s"
echo "Output: $OUT_FILE"
echo "Speak continuously for the whole capture."
read -r -p "Press Enter to start: "

set +e
timeout --signal=INT --kill-after=10s "${DURATION_SECONDS}s" \
  gst-launch-1.0 -e -m \
  videotestsrc is-live=true pattern=black \
    ! video/x-raw,width=1366,height=768,framerate=15/1 \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! x264enc bitrate=4500 speed-preset=veryfast tune=zerolatency key-int-max=60 \
    ! h264parse \
    ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=3000000000 \
    ! mux. \
  pulsesrc name=mic_src "device=$MIC" \
    buffer-time=500000 latency-time=20000 \
    provide-clock=false slave-method=resample \
    ! audioconvert \
    ! audioresample \
    ! audio/x-raw,rate=48000 \
    ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=3000000000 \
    ! avenc_aac bitrate=128000 \
    ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=3000000000 \
    ! mux. \
  mp4mux name=mux \
    reserved-max-duration=86400000000000 \
    reserved-moov-update-period=1000000000 \
    ! filesink "location=$OUT_FILE" \
  2>&1 | tee "$LOG_FILE"
rc=${PIPESTATUS[0]}
set -e

if [[ "$rc" -ne 0 && "$rc" -ne 124 && "$rc" -ne 130 ]]; then
  echo "Synthetic A/V capture failed with exit code $rc" >&2
  exit "$rc"
fi

echo
echo "Probe complete."
echo "Video: $OUT_FILE"
echo "Log:   $LOG_FILE"
echo
echo "Listen to the MP4 from beginning to end."
echo "Then search the log for WARNING, dropped samples, clock, and latency lines."
