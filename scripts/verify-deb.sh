#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.scientifica007.TroikaDLite"
PKG_NAME="troika-d-lite"

if [[ "$#" -ne 1 ]]; then
  echo "Usage: $0 /path/to/troika-d-lite_VERSION_all.deb" >&2
  exit 2
fi

DEB_PATH="$1"
if [[ ! -f "$DEB_PATH" ]]; then
  echo "Package not found: $DEB_PATH" >&2
  exit 1
fi

package="$(dpkg-deb --field "$DEB_PATH" Package)"
arch="$(dpkg-deb --field "$DEB_PATH" Architecture)"
depends="$(dpkg-deb --field "$DEB_PATH" Depends)"

[[ "$package" == "$PKG_NAME" ]]
[[ "$arch" == "all" ]]

required_depends=(
  python3
  python3-gi
  gir1.2-gtk-3.0
  gir1.2-gstreamer-1.0
  gstreamer1.0-pipewire
  gstreamer1.0-pulseaudio
  gstreamer1.0-plugins-base
  gstreamer1.0-plugins-good
  gstreamer1.0-plugins-bad
  gstreamer1.0-plugins-ugly
  gstreamer1.0-libav
  pulseaudio-utils
  xdg-desktop-portal
)

for dep in "${required_depends[@]}"; do
  if ! grep -Eq "(^|, )${dep}([ (]|,|$)" <<<"$depends"; then
    echo "Missing declared runtime dependency: $dep" >&2
    exit 1
  fi
done

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

dpkg-deb --extract "$DEB_PATH" "$stage"

required_files=(
  "usr/bin/troika-d-lite"
  "usr/lib/troika-d-lite/troika_d_lite/__main__.py"
  "usr/lib/troika-d-lite/troika_d_lite/app.py"
  "usr/lib/troika-d-lite/troika_d_lite/portal.py"
  "usr/lib/troika-d-lite/troika_d_lite/pipeline.py"
  "usr/lib/troika-d-lite/troika_d_lite/recorder.py"
  "usr/share/applications/$APP_ID.desktop"
  "usr/share/metainfo/$APP_ID.metainfo.xml"
  "usr/share/icons/hicolor/scalable/apps/$APP_ID.svg"
  "usr/share/doc/$PKG_NAME/LICENSE"
  "usr/share/doc/$PKG_NAME/RESPONSIBLE_USE.md"
  "usr/share/doc/$PKG_NAME/TRADEMARKS.md"
)

for rel in "${required_files[@]}"; do
  test -e "$stage/$rel" || {
    echo "Missing package payload: /$rel" >&2
    exit 1
  }
done

if find "$stage/usr/lib/troika-d-lite" \
  \( -type d -name '__pycache__' -o -type f -name '*.py[co]' \) \
  -print -quit | grep -q .; then
  echo "Python cache/bytecode leaked into Debian payload" >&2
  exit 1
fi

grep -F 'exec /usr/bin/python3 -m troika_d_lite "$@"' \
  "$stage/usr/bin/troika-d-lite" >/dev/null

if grep -F 'troika_d_lite ""' "$stage/usr/bin/troika-d-lite"; then
  echo "Launcher contains an install-time-expanded empty argument" >&2
  exit 1
fi

desktop-file-validate \
  "$stage/usr/share/applications/$APP_ID.desktop"

appstreamcli validate --no-net \
  "$stage/usr/share/metainfo/$APP_ID.metainfo.xml"

echo "Debian package verification: PASS"
