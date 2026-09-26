#!/usr/bin/env bash
set -euo pipefail

DURATION_SECONDS="${1:-90}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${2:-$ROOT_DIR/benchmark-results/mic001-$STAMP}"

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
if [[ -z "$MIC" ]]; then
  echo "Could not determine the default microphone source." >&2
  exit 1
fi
if [[ "$MIC" == *.monitor ]]; then
  echo "Refusing monitor source as microphone: $MIC" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

{
  echo "MIC-001 standalone microphone probe"
  echo "date=$(date --iso-8601=seconds)"
  echo "duration_seconds=$DURATION_SECONDS"
  echo "microphone_source=$MIC"
  echo
  pactl info || true
  echo
  pactl list short sources || true
} > "$OUT_DIR/environment.txt"

if pactl --format=json list sources >/dev/null 2>&1; then
  pactl --format=json list sources > "$OUT_DIR/sources.json"
fi

run_capture() {
  local label="$1"
  shift
  local wav="$OUT_DIR/$label.wav"
  local log="$OUT_DIR/$label.log"

  echo
  echo "================================================================"
  echo "$label"
  echo "Speak continuously during this capture."
  echo "Output: $wav"
  read -r -p "Press Enter to start ${DURATION_SECONDS}s capture: "

  set +e
  timeout --signal=INT --kill-after=5s "${DURATION_SECONDS}s" \
    gst-launch-1.0 -e -m \
    "$@" \
    audioconvert ! audioresample ! audio/x-raw,rate=48000 ! \
    wavenc ! filesink location="$wav" \
    2>&1 | tee "$log"
  rc=${PIPESTATUS[0]}
  set -e

  if [[ "$rc" -ne 0 && "$rc" -ne 124 && "$rc" -ne 130 ]]; then
    echo "Capture failed with exit code $rc" >&2
    exit "$rc"
  fi
}

run_capture \
  "01-app-style-pulsesrc" \
  pulsesrc \
  "device=$MIC" \
  buffer-time=500000 \
  latency-time=20000 \
  provide-clock=false \
  slave-method=resample \
  !

run_capture \
  "02-default-pulsesrc" \
  pulsesrc \
  "device=$MIC" \
  !

echo
echo "================================================================"
echo "MIC-001 probe complete."
echo "Results: $OUT_DIR"
echo
echo "Listen to both WAV files from beginning to end."
echo "If paplay is available:"
echo "  paplay '$OUT_DIR/01-app-style-pulsesrc.wav'"
echo "  paplay '$OUT_DIR/02-default-pulsesrc.wav'"
echo
echo "Interpretation:"
echo "  01 broken, 02 clean -> Lite explicit pulsesrc timing/clock options are suspect."
echo "  01 and 02 broken    -> Pulse/PipeWire/source path is suspect before Lite."
echo "  01 and 02 clean     -> A/V pipeline clock interaction becomes the primary suspect."
