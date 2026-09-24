# Project Origin and Independence

Troika D Lite is a new, independent repository created as a deliberately minimal companion to:

https://github.com/scientifica007/Troika-D

Both projects are maintained by the same project owner and are licensed under GPL-3.0-or-later.

## Why a separate repository exists

Troika D has grown into a broader screen-capture application supporting multiple capture modes and additional workflows.

Troika D Lite has a different product objective:

> minimize code paths, user choices, runtime complexity, and regression surface while preserving reliable full-screen video + audio recording.

A permanent “Lite branch” inside Troika D would not provide real product independence, and a monorepo/shared-core architecture is intentionally deferred until there is evidence that it is beneficial.

## Initial code policy

At repository foundation:

- no Troika D runtime source code is copied;
- no Window/Area/Webcam/Screenshot implementation is imported;
- no historical experimental branch is imported.

Future derivation from Troika D must be selective and documented.

## Lessons inherited from Troika D

The new project should preserve lessons already learned:

- technical pipeline success does not guarantee visually acceptable output;
- Portal Cancel is a normal user action, not an error;
- clean EOS and bounded finalization are both important;
- do not insert Python `__pycache__` or bytecode into Debian packages;
- declare GTK/GStreamer versions before GI imports to avoid GTK3/GDK3 vs GTK4 conflicts;
- avoid blind fullscreen overlays for Area selection on Wayland;
- do not treat hardware microphone gain/noise as an application DSP bug without independent evidence;
- CI is necessary but human field validation remains mandatory for media-pipeline changes.

## Current state

This repository intentionally begins with documentation and governance only.

Runtime implementation starts only after the product boundary is accepted.
