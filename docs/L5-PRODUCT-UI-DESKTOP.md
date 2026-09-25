# L5 — Minimal product UI and desktop integration

## Purpose

L5 turns the field-validated L1–L4 recorder into the intended minimal v0.1 product surface without adding recording capabilities.

The governing rule remains:

> Open → choose audio → Record → Stop.

## UI changes

The L5 UI keeps exactly the existing recording controls:

- Record microphone;
- microphone device selection;
- Record system audio;
- 15 FPS / 30 FPS;
- Start Recording;
- Stop Recording.

It does not add a Settings window, save-folder chooser, quality profiles, 60 FPS, capture modes, or other scope.

Product-level refinements:

- GNOME-style header bar;
- clearer Audio and Frame rate sections;
- theme-native suggested Start action;
- theme-native destructive Stop action;
- dedicated recording state;
- larger elapsed-time display;
- recording summary showing FPS and active audio mode;
- final status shows the actual saved path;
- initial status states the default output directory;
- existing pending-Portal controls remain frozen to prevent reentrant Start;
- repeated application activation presents the existing window rather than creating a second application window.

No hard-coded application color theme is introduced. The interface follows the desktop theme.

## Desktop integration source assets

L5 introduces source-controlled desktop integration metadata:

```text
data/
├── io.github.scientifica007.TroikaDLite.desktop
├── io.github.scientifica007.TroikaDLite.metainfo.xml
└── icons/hicolor/scalable/apps/
    └── io.github.scientifica007.TroikaDLite.svg
```

The desktop entry launches:

```text
troika-d-lite
```

The application ID, desktop file ID, icon name, and AppStream component ID intentionally match:

```text
io.github.scientifica007.TroikaDLite
```

L5 does not yet install these files into the system. Installation paths and Debian packaging belong to L6.

## Validation

CI validates:

- desktop-entry syntax;
- AppStream metadata;
- XML syntax of the scalable icon;
- existing GTK/GStreamer runtime imports;
- existing unit tests;
- focused product-UI helper tests.

## Human acceptance gate

**PASS — 2026-09-25.**

The focused Ubuntu 24.04 / Wayland check covered:

1. idle UI is compact, readable, and not visually cluttered;
2. microphone and system-audio controls behave as before;
3. 15/30 FPS controls behave as before;
4. Start enters the system screen-selection flow once;
5. Cancel restores the idle controls;
6. recording view clearly shows elapsed time and selected mode;
7. Stop remains reliable;
8. after Save, the status shows the actual path under `~/Videos`;
9. closing while recording remains safe;
10. no regression is observed in one dual-audio recording.

The desktop launcher itself is installed and tested in L6 together with packaging. L5 validates the source metadata only.

## Explicit non-goals

L5 does not add:

- new capture modes;
- new codecs;
- new audio processing;
- Settings;
- output-directory selection;
- notifications;
- tray icon;
- global shortcuts;
- translations;
- Debian packaging.

Those items either remain outside v0.1 or belong to a later explicitly approved milestone.


## Field validation status

**PASS — 2026-09-25.**

The focused product/UI gate passed against commit `6107dc335bd88970fc6374edeb9b81dd8ebde0d3`.

The human assessment described the interface as simple, practical, and visually good. Idle, Portal, Recording, and Saved states were exercised, and single-instance activation was confirmed from a second terminal invocation.

Because L5 does not modify the media pipeline or recorder lifecycle, the previously accepted L4 media matrix remains the media baseline rather than being duplicated as a new L5 matrix.

Detailed evidence:

- `docs/FIELD-TEST-L5-2026-09-25.md`
