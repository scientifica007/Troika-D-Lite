# L4 — Simultaneous microphone + system audio

## Purpose

L4 completes the v0.1 audio-state matrix by adding simultaneous microphone and system-audio recording.

After L4, the supported audio states are:

- microphone OFF / system audio OFF;
- microphone ON / system audio OFF;
- microphone OFF / system audio ON;
- microphone ON / system audio ON.

At 15 FPS and 30 FPS, these form the complete eight-case v0.1 recording matrix.

## User-visible behavior

The two audio checkboxes are now independent:

- Record microphone
- Record system audio

Both may be enabled at the same time.

Microphone selection remains available when microphone recording is enabled.

System audio continues to use the monitor associated with the default output sink. L4 does not introduce a system-audio source chooser.

## Dual-audio pipeline

Single-source behavior remains direct and unchanged:

```text
one Pulse/PipeWire source
  → convert/resample 48 kHz
  → bounded capture queue
  → AAC 128 kb/s
  → bounded mux queue
  → MP4
```

When both sources are enabled:

```text
microphone ─→ convert/resample 48 kHz ─→ bounded queue ─┐
                                                       ├→ audiomixer
system monitor → convert/resample 48 kHz → bounded queue ┘
     → final convert/resample 48 kHz
     → AAC 128 kb/s
     → bounded mux queue
     → MP4
```

The mixer latency baseline is 100 ms.

Each live source retains:

- `provide-clock=false`
- `slave-method=resample`
- 500 ms source buffer
- 20 ms requested latency

There is exactly one AAC encoder after the mixer.

## Stop/finalization

With dual audio active, source-level EOS must be sent to all three live sources:

- `screen_src`
- `mic_src`
- `system_audio_src`

Normal finalization still waits for mux EOS and retains the existing 12-second bounded fallback.

The isolated L3 video-only finalization recovery event remains documented and must be considered if similar events recur.

## Explicit exclusions

L4 does not add:

- per-source gain sliders;
- DSP/noise reduction;
- automatic ducking;
- separate audio tracks;
- audio-only mode;
- system-audio source chooser;
- camera;
- Window/Area capture;
- X11;
- 60 FPS;
- quality profiles.

The v0.1 contract remains one mixed audio track in MP4.

## Automated gate

CI must confirm at least:

- video-only remains audio-free;
- microphone-only contains no mixer;
- system-audio-only contains no mixer;
- dual audio contains both live sources;
- dual audio contains exactly one `audiomixer`;
- dual audio contains one AAC encoder after the mixer;
- Stop sends EOS to all three sources for dual audio;
- required native `audiomixer` element exists.

## Human acceptance gate

L4 is not accepted until Ubuntu 24.04 / Wayland testing confirms the full eight-case matrix:

| FPS | Microphone | System audio |
| --- | --- | --- |
| 15 | OFF | OFF |
| 15 | ON | OFF |
| 15 | OFF | ON |
| 15 | ON | ON |
| 30 | OFF | OFF |
| 30 | ON | OFF |
| 30 | OFF | ON |
| 30 | ON | ON |

For the two dual-audio cases in particular, confirm:

- both microphone speech and system playback are audible;
- neither source disappears from the mix;
- synchronization remains acceptable;
- no obvious clipping or severe distortion occurs under ordinary source levels;
- normal Stop produces playable MP4;
- close-while-recording finalizes safely;
- external Portal Stop returns safely to idle;
- no reproducible finalization timeout appears.

A longer dual-audio run of at least two to three minutes is required to check drift.
