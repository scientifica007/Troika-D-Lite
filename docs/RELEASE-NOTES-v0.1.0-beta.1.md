# Troika D Lite v0.1.0-beta.1

This is the first public beta of Troika D Lite.

Troika D Lite is a deliberately small Linux screen recorder built around one workflow:

> **Open → choose audio → Record → Stop**

## Target platform

Primary validated target:

- Ubuntu 24.04 LTS;
- Wayland;
- XDG Desktop Portal;
- PipeWire.

X11 is not claimed as supported in this beta because it has not completed the same field-validation process.

## Included in this beta

- Full Screen recording;
- 15 FPS and 30 FPS;
- MP4 / H.264 output;
- video only;
- microphone only;
- system audio only;
- mixed microphone + system audio;
- microphone selection and idle hot-plug refresh;
- collision-safe output under `~/Videos`;
- clean Portal Cancel handling;
- bounded Stop/finalization;
- GNOME desktop launcher, icon, and AppStream metadata;
- native Debian/Ubuntu package.

## Field validation

The beta candidate passed:

- all eight required FPS/audio combinations;
- microphone hot-plug and selection;
- system-side Portal Stop;
- dual-audio field testing;
- Debian install/remove validation;
- performance benchmarking;
- repeated Lite vs Troika D controlled comparison;
- final installed-package long dual-audio recording.

A low-motion CPU regression caused by Lite's former live elapsed-time label was found during benchmarking. Because Full Screen capture includes the recorder window itself, updating that label once per second generated additional compositor/PipeWire work. The live timer was removed, and the corrected visible-window benchmark passed.

## Known limitations and observations

- Full Screen only: no Window or Area capture.
- No Webcam, Screenshot, Pause/Resume, 60 FPS, profiles, editing, effects, or streaming.
- The desktop Share Screen Portal dialog may show a system-side text-rendering artifact on some graphics configurations; this is outside the Lite GTK window and did not block recording.
- On the field machine, an extreme local-video + workspace-switch workload could make the entire desktop stutter. The same stutter reproduced with no recorder running, so it is classified as a host/video-player/compositor capacity condition rather than a Lite-specific defect.
- Stop/finalization is bounded. Some low-motion field runs took several seconds to finalize but remained below the 12-second timeout and ended through normal EOS.

## Release identity

- Git tag: `v0.1.0-beta.1`
- Python package: `0.1.0b1`
- Debian package: `0.1.0~beta1-1`
- AppStream release: `0.1.0-beta.1`

## Debian installation

GitHub normalizes the `~` character in uploaded asset filenames to `.`.
The Debian package version **inside the package** remains `0.1.0~beta1-1`,
while the published GitHub asset is named:

```text
troika-d-lite_0.1.0.beta1-1_all.deb
```

After downloading the release asset:

```bash
sudo apt install ./troika-d-lite_0.1.0.beta1-1_all.deb
```

Run from the application launcher or:

```bash
troika-d-lite
```

Recordings are saved under:

```text
~/Videos
```

## License

GPL-3.0-or-later.
