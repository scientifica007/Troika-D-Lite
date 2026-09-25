#!/usr/bin/env bash
set -euo pipefail

declare -A EXPECTED=(
  [pipewiresrc]="gstreamer1.0-pipewire"
  [pulsesrc]="gstreamer1.0-pulseaudio"
  [audiomixer]="gstreamer1.0-plugins-base"
  [mp4mux]="gstreamer1.0-plugins-good"
  [h264parse]="gstreamer1.0-plugins-bad"
  [x264enc]="gstreamer1.0-plugins-ugly"
  [avenc_aac]="gstreamer1.0-libav"
)

for element in "${!EXPECTED[@]}"; do
  expected="${EXPECTED[$element]}"
  output="$(gst-inspect-1.0 "$element")"
  filename="$(
    awk -F': ' '/^[[:space:]]*Filename[[:space:]]*:/ {print $2; exit}' \
      <<<"$output"
  )"
  if [[ -z "$filename" ]]; then
    echo "Could not resolve plugin file for $element" >&2
    exit 1
  fi

  real="$(readlink -f "$filename")"
  owner_line="$(dpkg-query -S "$real" 2>/dev/null | head -n1 || true)"
  owner="${owner_line%%:*}"

  if [[ "$owner" != "$expected" ]]; then
    echo "Unexpected package for $element: expected=$expected actual=$owner file=$real" >&2
    exit 1
  fi
  printf 'PASS  %-16s -> %s\n' "$element" "$owner"
done

pactl_path="$(command -v pactl)"
pactl_owner_line="$(dpkg-query -S "$pactl_path" | head -n1)"
pactl_owner="${pactl_owner_line%%:*}"
[[ "$pactl_owner" == "pulseaudio-utils" ]] || {
  echo "Unexpected package for pactl: $pactl_owner" >&2
  exit 1
}
printf 'PASS  %-16s -> %s\n' "pactl" "$pactl_owner"

for package in \
  python3-gi \
  gir1.2-gtk-3.0 \
  gir1.2-gstreamer-1.0 \
  xdg-desktop-portal
do
  dpkg-query -W -f='${Status}\n' "$package" 2>/dev/null \
    | grep -qx 'install ok installed' || {
      echo "Required package not installed during audit: $package" >&2
      exit 1
    }
  printf 'PASS  package          -> %s\n' "$package"
done

echo "Runtime dependency ownership audit: PASS"
