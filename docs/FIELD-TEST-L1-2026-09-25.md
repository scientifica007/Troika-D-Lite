# L1 Field Test — 2026-09-25

## Tested build

Repository: `scientifica007/Troika-D-Lite`

Branch: `milestone/l1-video-only`

Runtime commit tested:

```
69de46486933b6c8eec0e6928af1bccb1367f092
```

Target environment: Ubuntu 24.04 / Wayland, using the normal XDG Desktop Portal screen-share flow.

## Human acceptance result

The complete L1 human field gate was reported PASS on 2026-09-25.

1. 30 FPS video-only recording — PASS.
2. 15 FPS video-only recording — PASS.
3. Portal Cancel — PASS. Cancellation returned cleanly without an error dialog.
4. Normal Stop/finalization — PASS. Output saved successfully.
5. Closing the application while recording — PASS. Safe finalization behavior worked.
6. System/GNOME-side screen-share Stop — PASS.
7. Visual acceptance — PASS. Recording quality was reported good and smooth, with no observed green corruption, checkerboard corruption, or other visible problem.

Screenshots supplied during the field test also showed the expected states:

- idle UI with 15/30 FPS selection;
- system Share Screen portal;
- clean `Screen selection cancelled` state;
- active recording UI and GNOME screen-share indicator;
- successful return to idle with `Saved`.

## GStreamer videorate diagnostics

The following counters were captured from the tested build:

```text
Video timing stats [eos] fps=30 in=1555 out=2423 drop=120 duplicate=988
Video timing stats [eos] fps=15 in=1755 out=1248 drop=714 duplicate=207
Video timing stats [external-portal-stop] fps=15 in=32 out=19 drop=15 duplicate=3
Video timing stats [external-portal-stop] fps=30 in=92 out=171 drop=7 duplicate=86
Video timing stats [eos] fps=30 in=122 out=175 drop=10 duplicate=63
```

These counters are retained as diagnostic baseline data, not as standalone quality verdicts.

`videorate` is intentionally converting a variable input cadence into the requested constant output cadence. Therefore `drop` and `duplicate` counts must be interpreted together with the input/output cadence, recording duration, source behavior, and human visual result.

The field result was visually smooth and acceptable, so L1 does not change the field-tested Full Screen pipeline merely to reduce these counters. They should be revisited during the dedicated performance/benchmark milestone using controlled workloads and comparable runs.

## Stop/finalization observations

No finalization timeout was reported.

Normal EOS completed successfully.

External Portal/GNOME stop was handled without leaving the application in a broken state.

The L1 safety model therefore passed the human field gate:

- source-level EOS;
- pipeline EOS fallback when needed;
- bounded finalization;
- robust MP4 state;
- Portal cleanup;
- PipeWire fd cleanup;
- external `Session::Closed` handling.

## L1 decision

**L1 HUMAN FIELD GATE: PASS**

The L1 video-only vertical slice is acceptable as the first stable runtime baseline for Troika D Lite.

This decision validates only the L1 scope. It does not yet validate microphone audio, system audio, mixed audio, packaging, or final performance targets.
