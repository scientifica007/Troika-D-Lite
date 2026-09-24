# L2 — Optional microphone audio

## Purpose

L2 adds exactly one new media capability to the accepted L1 baseline:

> full-screen video + optional microphone audio.

System audio remains out of scope for L2.

## User-visible scope

L2 adds:

- Record microphone ON/OFF.
- Microphone selection from currently available non-monitor Pulse/PipeWire sources.
- Automatic device refresh while idle.
- An immediate refresh before Start so a just-connected microphone is not missed.

Microphone recording is OFF by default.

The existing 15 FPS / 30 FPS and Start / Stop behavior remains unchanged.

## Audio path

When microphone recording is enabled:

```text
Pulse/PipeWire microphone
  → pulsesrc
  → audioconvert
  → audioresample
  → 48 kHz
  → bounded queue
  → AAC 128 kb/s
  → bounded mux queue
  → MP4 mux
```

The microphone source preserves the field-tested Troika D timing behavior:

- `provide-clock=false`
- `slave-method=resample`
- 500 ms source buffer
- 20 ms requested latency
- 48 kHz raw audio before AAC

No DSP, denoising, automatic gain processing, or application-level microphone boost is introduced.

## Device discovery and hot-plug

L2 derives only the microphone-relevant part of Troika D device discovery.

- `pactl --format=json list sources` is preferred.
- monitor/system-audio sources are excluded.
- a short-list fallback is retained for compatibility.
- the Pulse/PipeWire default source is preferred when available.
- devices are refreshed every two seconds while the recorder is idle.
- capture performs one additional refresh immediately before Start.
- device polling does not perform work while a recording is active.

This specifically preserves the field lesson that a microphone connected after application startup must become usable without restarting the application.

## Stop/finalization

L1 pushed EOS from `screen_src`.

L2 must push EOS from every active live capture source:

- `screen_src`
- `mic_src`, when present.

Only if source-level EOS is not accepted does the recorder fall back to pipeline-level EOS.

The existing 12-second bounded finalization and robust MP4 behavior remain unchanged.

## Explicit exclusions

L2 does not add:

- system audio;
- microphone + system mixing;
- `audiomixer`;
- audio-only mode;
- DSP/noise reduction;
- gain controls;
- camera;
- Window or Area capture;
- X11;
- 60 FPS;
- quality profiles.

## Human acceptance gate

**PASS — 2026-09-25.**

Ubuntu 24.04 / Wayland field testing confirmed:

1. video-only 15 FPS remains good;
2. video-only 30 FPS remains good;
3. microphone + video at 15 FPS is playable and synchronized;
4. microphone + video at 30 FPS is playable and synchronized;
5. external microphone hot-plug after application startup is detected;
6. microphone device selection works when more than one source is available;
7. normal Stop produces a playable finalized MP4 with audio;
8. close-while-recording finalizes safely with microphone enabled;
9. system-side Portal Stop does not leave a stuck recording;
10. no unacceptable video regression, audio drift, broken audio, or finalization timeout is observed.

Built-in microphone noise or gain must not be classified as an application defect without independent evidence that the recording path itself is responsible.


## Field validation status

**PASS — 2026-09-25.**

The human L2 field gate passed against runtime commit `95e6a6fabe8409f5371253a1bd79b58afb58f9b2`.

Validated behaviors include video-only regression checks, microphone recording at 15/30 FPS, external microphone hot-plug, multiple-device selection, normal Stop/finalization, close-while-recording, system-side Portal Stop, and longer-run synchronization.

Detailed evidence and diagnostics are recorded in:

- `docs/FIELD-TEST-L2-2026-09-25.md`
