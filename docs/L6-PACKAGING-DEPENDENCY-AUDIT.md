# L6 — Packaging and dependency audit

## Purpose

L6 turns the accepted L5 source application into a native Debian/Ubuntu-installable product and audits the runtime dependency contract.

L6 does not change the recorder pipeline or product feature scope.

## Distribution outputs

L6 validates three build outputs:

1. Python wheel;
2. Python source distribution;
3. native `.deb` package.

The native Debian package is the intended Ubuntu user distribution path for v0.1.

A separate user-local installer is intentionally not added in L6. The product specification marks it optional, and the native package already provides the required command, desktop launcher, icon, and metadata with a smaller maintenance surface.

## Debian filesystem layout

The package installs:

```text
/usr/bin/troika-d-lite
/usr/lib/troika-d-lite/troika_d_lite/
/usr/share/applications/io.github.scientifica007.TroikaDLite.desktop
/usr/share/metainfo/io.github.scientifica007.TroikaDLite.metainfo.xml
/usr/share/icons/hicolor/scalable/apps/io.github.scientifica007.TroikaDLite.svg
/usr/share/doc/troika-d-lite/
```

The launcher executes:

```text
/usr/bin/python3 -m troika_d_lite
```

with `/usr/lib/troika-d-lite` added to `PYTHONPATH`.

## Runtime dependency audit

The package declares the dependencies needed by the actual L1–L5 runtime.

| Runtime need | Debian/Ubuntu package |
| --- | --- |
| Python GI | `python3-gi` |
| GTK 3 typelib | `gir1.2-gtk-3.0` |
| GStreamer typelib | `gir1.2-gstreamer-1.0` |
| `pipewiresrc` | `gstreamer1.0-pipewire` |
| `pulsesrc` | `gstreamer1.0-plugins-good` |
| conversion/resample/mixer base elements | `gstreamer1.0-plugins-base` |
| MP4 muxer | `gstreamer1.0-plugins-good` |
| H.264 parser | `gstreamer1.0-plugins-bad` |
| x264 encoder | `gstreamer1.0-plugins-ugly` |
| AAC encoder | `gstreamer1.0-libav` |
| `pactl` discovery | `pulseaudio-utils` |
| ScreenCast Portal service | `xdg-desktop-portal` |

`pipewire` and a desktop Portal backend are recommendations because the application targets an Ubuntu/Wayland desktop session where those services are expected to be provided by the environment.

L6 explicitly declares `gstreamer1.0-pipewire` because it owns `pipewiresrc`. The Ubuntu 24.04 ownership audit established that `pulsesrc` is supplied by `gstreamer1.0-plugins-good`, so the separate `gstreamer1.0-pulseaudio` package is intentionally not declared as a Lite runtime dependency.

`gstreamer1.0-tools` is a CI/diagnostic tool and is not a runtime package dependency.

## Dependency ownership check

`scripts/audit-runtime-deps.sh` verifies on Ubuntu CI that key GStreamer elements are actually supplied by the packages declared above.

This catches accidental assumptions such as a required element being present only because the CI image happened to contain an unrelated package.

## Package hygiene

The package builder:

- stages into a temporary directory;
- strips `__pycache__`, `*.pyc`, and `*.pyo`;
- installs only Lite runtime modules and approved metadata/docs;
- preserves the launcher argument vector as `"$@"`;
- uses a collision-free temporary staging directory;
- builds with root ownership metadata through `dpkg-deb --root-owner-group`.

`scripts/verify-deb.sh` rejects:

- missing required payload files;
- missing declared runtime dependencies;
- Python cache/bytecode leakage;
- a launcher with the historical empty-argument expansion defect;
- invalid desktop metadata;
- invalid AppStream metadata.

## CI gate

L6 CI must pass:

- existing L1–L5 tests;
- runtime dependency ownership audit;
- desktop/AppStream validation;
- wheel and source-distribution build;
- Debian package build;
- Debian package structural verification;
- Lintian errors gate;
- APT installation of the generated local package;
- installed command/desktop/icon/metainfo/import checks;
- package removal.

## Human acceptance gate

**PASS — 2026-09-25.**

The generated package was installed on the Ubuntu 24.04 / Wayland field machine and verified:

1. package installs without manual copying;
2. `troika-d-lite` is available as a command;
3. Troika D Lite appears in the application launcher with its icon;
4. launcher opens exactly one application window;
5. one 30 FPS recording completes successfully;
6. microphone and system-audio controls are present;
7. saved output still goes to `~/Videos`;
8. package can be removed cleanly.

A full eight-case media matrix is not repeated in L6 because packaging does not modify the accepted media pipeline.

## Explicit non-goals

L6 does not:

- publish a GitHub Release;
- assign beta/stable release status;
- add AppImage or Flatpak;
- add a user-local installer;
- change recording behavior;
- perform the final performance benchmark.

Those belong to later milestones or require a separate product decision.


## Field validation status

**PASS — 2026-09-25.**

The native `.deb` was built from commit `4bedf353a32d203c67fea06c783436b0b9cfb2d1`, installed with APT, launched from GNOME with its packaged icon, used for a normal 30 FPS system-audio recording, and removed cleanly.

A transient post-remove `command -v` result was traced to Bash command hashing. Direct filesystem checks confirmed `/usr/bin/troika-d-lite` was absent, and `hash -r` cleared the stale shell lookup.

Detailed evidence:

- `docs/FIELD-TEST-L6-2026-09-25.md`
