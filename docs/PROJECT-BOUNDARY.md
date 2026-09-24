# Project Boundary

This document exists to prevent Troika D Lite from gradually becoming a second copy of Troika D.

## Product boundary

Troika D Lite exists for:

> full-screen video recording + optional microphone/system audio.

The first implementation may expose only:

- 15/30 FPS;
- microphone ON/OFF;
- system audio ON/OFF;
- microphone device selection when materially necessary;
- Start;
- Stop.

## Features that belong in Troika D, not Lite

Unless the product specification is explicitly revised, the following remain outside Lite:

- Window capture;
- Area capture;
- Webcam;
- Screenshot;
- Pause/Resume;
- 60 FPS;
- multiple quality presets;
- effects;
- editing;
- streaming;
- multi-scene workflows;
- advanced capture-source configuration.

## Engineering boundary

Do not copy the complete Troika D repository and delete unwanted features.

Instead:

1. identify the minimum field-proven behavior needed;
2. understand its dependencies;
3. move or reimplement only that minimum;
4. add tests around each imported behavior;
5. compare real field behavior against Troika D where relevant.

## Shared-core policy

Do **not** create a shared `troika-core` package at the start of the project.

A shared core may be evaluated later only if both products independently stabilize and real duplicated code justifies extraction.

Premature shared-core refactoring would create unnecessary coupling and regression risk for Troika D.

## Change rule

Any feature outside the current boundary requires an explicit product decision before implementation.
