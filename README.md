# Troika D Lite

**Minimal, dependable screen-and-audio recording for Linux.**

Troika D Lite is a deliberately small companion project to [Troika D](https://github.com/scientifica007/Troika-D).

Its first product goal is intentionally narrow:

> **Open → choose audio → Record → Stop**

The v0.1 scope is limited to:

- full-screen video recording;
- microphone audio, optional;
- system audio, optional;
- microphone + system audio together;
- 15 FPS and 30 FPS;
- MP4/H.264 output;
- Ubuntu 24.04 / Wayland first;
- robust Stop/finalization;
- native desktop integration and Debian packaging.

It intentionally excludes Window capture, Area capture, Webcam, Screenshot, Pause/Resume, 60 FPS, multiple quality profiles, editing, effects, and streaming.

## Project status

**Foundation / specification stage.**

No runtime recorder code is intentionally present yet. The project starts from a clean repository so only the minimum proven pieces needed from Troika D are introduced later.

Before implementation, read:

- `docs/MINI-PRODUCT-SPEC-v0.1.md`
- `docs/PROJECT-BOUNDARY.md`
- `docs/ORIGIN.md`

## Relationship to Troika D

Troika D Lite is not intended to replace Troika D.

- **Troika D** remains the broader recorder.
- **Troika D Lite** is a single-purpose recorder optimized for simplicity, low complexity, and low-resource machines.

Code may later be selectively derived from field-tested Troika D components, but the full Troika D codebase must not be copied wholesale into this repository.

## License

Troika D Lite is licensed under **GPL-3.0-or-later**.

See:

- `LICENSE`
- `RESPONSIBLE_USE.md`
- `TRADEMARKS.md`
