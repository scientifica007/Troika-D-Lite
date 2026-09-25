#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.scientifica007.TroikaDLite"
PKG_NAME="troika-d-lite"
DEB_VERSION="${TROIKA_D_LITE_DEB_VERSION:-0.1.0~beta1-1}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT_DIR/dist-deb}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

PKG_ROOT="$STAGE/$PKG_NAME"
CONTROL_DIR="$PKG_ROOT/DEBIAN"
APP_LIB="/usr/lib/$PKG_NAME"
DOC_DIR="/usr/share/doc/$PKG_NAME"

mkdir -p \
  "$CONTROL_DIR" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT$APP_LIB" \
  "$PKG_ROOT/usr/share/applications" \
  "$PKG_ROOT/usr/share/metainfo" \
  "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps" \
  "$PKG_ROOT$DOC_DIR"

cp -a "$ROOT_DIR/src/troika_d_lite" \
  "$PKG_ROOT$APP_LIB/troika_d_lite"

# Never ship development bytecode/cache from a working tree.
find "$PKG_ROOT$APP_LIB" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$PKG_ROOT$APP_LIB" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

install -m 0644 \
  "$ROOT_DIR/data/$APP_ID.desktop" \
  "$PKG_ROOT/usr/share/applications/$APP_ID.desktop"

install -m 0644 \
  "$ROOT_DIR/data/$APP_ID.metainfo.xml" \
  "$PKG_ROOT/usr/share/metainfo/$APP_ID.metainfo.xml"

install -m 0644 \
  "$ROOT_DIR/data/icons/hicolor/scalable/apps/$APP_ID.svg" \
  "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps/$APP_ID.svg"

install -m 0644 "$ROOT_DIR/LICENSE" "$PKG_ROOT$DOC_DIR/LICENSE"
install -m 0644 "$ROOT_DIR/RESPONSIBLE_USE.md" "$PKG_ROOT$DOC_DIR/RESPONSIBLE_USE.md"
install -m 0644 "$ROOT_DIR/TRADEMARKS.md" "$PKG_ROOT$DOC_DIR/TRADEMARKS.md"

cat > "$PKG_ROOT$DOC_DIR/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Troika D Lite
Source: https://github.com/scientifica007/Troika-D-Lite

Files: *
Copyright: 2026 Scientifica
License: GPL-3+
 Troika D Lite is free software: you can redistribute it and/or modify it
 under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 On Debian systems, the complete text of the GNU General Public
 License version 3 can be found in /usr/share/common-licenses/GPL-3.
EOF

cat > "$STAGE/changelog.Debian" <<EOF
troika-d-lite ($DEB_VERSION) unstable; urgency=medium

  * First public beta package for Troika D Lite v0.1.

 -- Scientifica <scientifica007@users.noreply.github.com>  Fri, 25 Sep 2026 00:00:00 +0000
EOF
gzip -n -9 -c "$STAGE/changelog.Debian" > \
  "$PKG_ROOT$DOC_DIR/changelog.Debian.gz"

cat > "$PKG_ROOT/usr/bin/troika-d-lite" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/usr/lib/troika-d-lite${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m troika_d_lite "$@"
EOF
chmod 0755 "$PKG_ROOT/usr/bin/troika-d-lite"

cat > "$CONTROL_DIR/control" <<EOF
Package: $PKG_NAME
Version: $DEB_VERSION
Section: video
Priority: optional
Architecture: all
Maintainer: Scientifica <scientifica007@users.noreply.github.com>
Homepage: https://github.com/scientifica007/Troika-D-Lite
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-gstreamer-1.0, gstreamer1.0-pipewire, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good, gstreamer1.0-plugins-bad, gstreamer1.0-plugins-ugly, gstreamer1.0-libav, pulseaudio-utils, xdg-desktop-portal
Recommends: pipewire, xdg-desktop-portal-gnome | xdg-desktop-portal-gtk
Description: minimal screen and audio recorder for Linux
 Troika D Lite records the full screen with optional microphone and system
 audio. It targets Ubuntu 24.04 / Wayland first and intentionally keeps a
 small recording surface: 15/30 FPS, H.264/MP4, Start and Stop.
EOF

cat > "$CONTROL_DIR/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 0755 "$CONTROL_DIR/postinst"

cat > "$CONTROL_DIR/postrm" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 0755 "$CONTROL_DIR/postrm"

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/${PKG_NAME}_${DEB_VERSION}_all.deb"

dpkg-deb --build --root-owner-group "$PKG_ROOT" "$OUT" >/dev/null
echo "$OUT"
