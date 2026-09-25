# Troika D Lite

**Minimal, dependable screen-and-audio recording for Linux.**

Troika D Lite is a deliberately small companion project to [Troika D](https://github.com/scientifica007/Troika-D).

Its product rule is intentionally narrow:

> **Open → choose audio → Record → Stop**

## Current status

The core v0.1 recorder and minimal product UI are implemented and field-validated on Ubuntu 24.04 / Wayland through L5.

Validated recording states:

- full-screen video only;
- full-screen + microphone;
- full-screen + system audio;
- full-screen + microphone + system audio;
- 15 FPS and 30 FPS;
- MP4/H.264 output;
- Portal Cancel;
- normal Stop/finalization;
- system-side Portal Stop;
- microphone hot-plug and selection.

L6 adds native Debian/Ubuntu packaging and an explicit runtime dependency audit. The package is still a development artifact until the L6 human installation gate passes.

## Product boundary

Troika D Lite intentionally excludes:

- Window capture;
- Area capture;
- Webcam;
- Screenshot;
- Pause/Resume;
- 60 FPS;
- multiple quality profiles;
- editing;
- effects;
- streaming.

The v0.1 output directory is:

```text
~/Videos
```

Files are timestamped and collision-safe.

## Run from source

On a supported Ubuntu 24.04 / Wayland system with the required native dependencies installed:

```bash
PYTHONPATH=src /usr/bin/python3 -m troika_d_lite
```

The installed command entry point is:

```text
troika-d-lite
```

The L6 Debian package installs the command, desktop launcher, icon, and AppStream metadata.

## Documentation

Start with:

- `docs/MINI-PRODUCT-SPEC-v0.1.md`
- `docs/PROJECT-BOUNDARY.md`
- `docs/L1-VIDEO-ONLY.md`
- `docs/L2-MICROPHONE.md`
- `docs/L3-SYSTEM-AUDIO.md`
- `docs/L4-DUAL-AUDIO.md`
- `docs/L5-PRODUCT-UI-DESKTOP.md`
- `docs/L6-PACKAGING-DEPENDENCY-AUDIT.md`

Field-test evidence is kept under `docs/FIELD-TEST-*.md`.

## Relationship to Troika D

Troika D Lite is not intended to replace Troika D.

- **Troika D** remains the broader recorder.
- **Troika D Lite** is a single-purpose recorder optimized for simplicity, low complexity, and low-resource machines.

Only the minimum proven behavior needed by Lite is selectively derived from Troika D.

## License

Troika D Lite is licensed under **GPL-3.0-or-later**.

See:

- `LICENSE`
- `RESPONSIBLE_USE.md`
- `TRADEMARKS.md`
