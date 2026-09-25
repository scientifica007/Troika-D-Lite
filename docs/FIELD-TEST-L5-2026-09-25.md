# L5 Field Test — 2026-09-25

## Tested build

Repository: `scientifica007/Troika-D-Lite`

Branch: `milestone/l5-product-ui-desktop`

Runtime commit tested:

```
6107dc335bd88970fc6374edeb9b81dd8ebde0d3
```

Target environment: Ubuntu 24.04 / Wayland.

## Scope of this gate

L5 changes product presentation and desktop-integration source metadata. It does not change the accepted L1–L4 media pipeline, Portal implementation, audio discovery, or recorder finalization logic.

Therefore the L5 human gate is a focused product/UI regression gate, while the full media matrix remains covered by the accepted L4 evidence.

## Human result

**L5 focused human field gate: PASS**

Observed and accepted:

- idle UI is compact, readable, and visually simple;
- Audio and Frame rate sections are clearly separated;
- Start Recording is prominent without adding extra configuration;
- the system Share Screen flow opens correctly;
- the recording view clearly shows the recording state, elapsed time, FPS, and audio mode;
- Stop Recording remains prominent and usable;
- a normal 30 FPS video-only recording finalized through clean EOS;
- after Stop, the UI shows the actual saved path under `~/Videos`;
- launching a second `troika_d_lite` process while the application is already running does not create a second application window.

Representative normal Stop:

```text
EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=0 system=0 in=980 out=3201 drop=89 duplicate=2310
```

No recording error, pipeline fallback, or finalization timeout was reported.

## UI assessment

The human assessment of the L5 interface was:

> simple, practical, and visually good.

The interface remains within the Lite product boundary: there is no Settings page, output chooser, quality profile, extra capture mode, or other scope expansion.

## Single-instance behavior

A second terminal invocation:

```bash
PYTHONPATH=src /usr/bin/python3 -m troika_d_lite
```

returned without creating another Troika D Lite window while the existing application instance remained active.

**Single-instance behavior: PASS.**

## Existing Portal rendering observation

The previously documented partially erased text inside the system Share Screen dialog remains an external Portal/compositor observation. L5 does not introduce an application-side workaround because Troika D Lite does not render that system dialog.

## L5 decision

**L5 HUMAN FIELD GATE: PASS**

L5 is accepted as the minimal v0.1 product UI baseline.

Desktop launcher installation and package-level verification remain L6 scope.
