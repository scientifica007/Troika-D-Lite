# L2 Field Test — 2026-09-25

## Tested build

Repository: `scientifica007/Troika-D-Lite`

Branch: `milestone/l2-microphone`

Runtime commit tested:

```
95e6a6fabe8409f5371253a1bd79b58afb58f9b2
```

Target environment: Ubuntu 24.04 / Wayland.

## Human acceptance result

The complete L2 human field gate was reported PASS on 2026-09-25.

Validated:

1. Video-only 15 FPS remained good.
2. Video-only 30 FPS remained good.
3. Microphone + video at 15 FPS was playable and synchronized.
4. Microphone + video at 30 FPS was playable and synchronized.
5. External microphone hot-plug after application startup was detected.
6. Multiple microphone sources were exposed and selectable.
7. Normal Stop produced finalized MP4 output with microphone audio.
8. Close-while-recording finalized safely with microphone enabled.
9. System-side Portal/GNOME Stop returned the application safely to idle.
10. Longer microphone recording showed no unacceptable audio drift, broken audio, video regression, or finalization timeout.

## Device discovery evidence

The UI initially exposed the built-in source:

```text
Built-in Audio Analog Stereo
```

After connecting the external microphone, the application reported:

```text
Microphone devices updated
```

and exposed both:

```text
Built-in Audio Analog Stereo
CM108 Audio Controller Mono
```

This validates the L2 idle hot-plug refresh behavior without requiring an application restart.

## EOS/finalization evidence

Representative successful microphone Stop operations:

```text
EOS request: source-pads=[screen_src:1,mic_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=1 in=401 out=338 drop=190 duplicate=127

EOS request: source-pads=[screen_src:1,mic_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=1 in=392 out=539 drop=30 duplicate=177

EOS request: source-pads=[screen_src:1,mic_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=1 in=4306 out=2730 drop=1612 duplicate=36
```

Repeated microphone-enabled normal Stop operations consistently showed both active live sources accepting source-level EOS and no pipeline-level fallback.

Video-only behavior also remained intact:

```text
EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=0 in=944 out=1580 drop=52 duplicate=688
```

## External Portal Stop evidence

Representative external/system-side Stop diagnostics:

```text
Video timing stats [external-portal-stop] fps=15 mic=1 in=126 out=95 drop=59 duplicate=29
Video timing stats [external-portal-stop] fps=15 mic=1 in=73 out=68 drop=30 duplicate=26
```

The UI returned safely to idle and displayed the expected system-stop status.

## Videorate diagnostics

The collected `drop` and `duplicate` counters are retained as baseline diagnostics only.

They are not treated as standalone quality failures. The L2 human visual and audio acceptance result was successful, including the longer microphone run. Any optimization of cadence behavior belongs to the dedicated performance milestone and must not destabilize the field-accepted Full Screen pipeline without evidence.

## L2 decision

**L2 HUMAN FIELD GATE: PASS**

L2 is accepted as the stable microphone-capable baseline.

This validates microphone recording only. It does not yet validate system audio or microphone + system-audio mixing, which remain future milestones.
