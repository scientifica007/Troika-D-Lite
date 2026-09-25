# L3 — Optional system audio

## Purpose

L3 adds one new media capability to the accepted L2 baseline:

> full-screen video + optional system audio.

The accepted microphone path remains unchanged.

Microphone + system-audio mixing remains out of scope until L4.

## User-visible scope

L3 adds:

- Record system audio ON/OFF.
- Automatic selection of the monitor source associated with the current default output sink.
- Audio-device refresh while idle.

To keep L3 isolated, microphone and system audio are temporarily mutually exclusive in the UI. Enabling one disables the other. L4 removes this transitional restriction and adds simultaneous mixing.

No system-audio device chooser is exposed in L3. The Lite product should use the default output monitor unless field evidence shows a real need for additional choice.

## System-audio path

When system audio is enabled:

```text
Default output sink monitor
  → pulsesrc
  → audioconvert
  → audioresample
  → 48 kHz
  → bounded queue
  → AAC 128 kb/s
  → bounded mux queue
  → MP4 mux
```

The source uses the same field-proven timing behavior as microphone capture:

- `provide-clock=false`
- `slave-method=resample`
- 500 ms source buffer
- 20 ms requested latency
- 48 kHz raw audio before AAC

## Monitor discovery

L3 derives the monitor-source behavior already proven in Troika D:

1. enumerate Pulse/PipeWire sources through `pactl`;
2. keep sources identified as sink monitors;
3. query the current default sink;
4. prefer `<default-sink>.monitor`;
5. fall back to the first available monitor only when the exact default monitor cannot be found.

The audio-device list is refreshed while idle and once more immediately before Start.

## Stop/finalization

L3 extends source-level EOS handling to:

- `screen_src`
- `mic_src`, when microphone recording is used
- `system_audio_src`, when system audio is used

The existing pipeline-level EOS fallback, 12-second finalization bound, robust MP4 state, Portal cleanup, and PipeWire fd cleanup remain unchanged.

## Explicit exclusions

L3 does not add:

- simultaneous microphone + system audio;
- `audiomixer`;
- system-audio source chooser;
- audio-only mode;
- DSP/noise reduction;
- gain controls;
- camera;
- Window or Area capture;
- X11;
- 60 FPS;
- quality profiles.

## Human acceptance gate

L3 is not accepted until Ubuntu 24.04 / Wayland field testing confirms:

1. video-only behavior remains good;
2. microphone recording remains good;
3. system audio at 15 FPS is audible, playable, and synchronized;
4. system audio at 30 FPS is audible, playable, and synchronized;
5. normal Stop with system audio finalizes a playable MP4;
6. close-while-recording with system audio finalizes safely;
7. system-side Portal Stop returns safely to idle;
8. the default output monitor is selected correctly;
9. changing the default output while idle is reflected without restarting the application;
10. no unacceptable video regression, audio drift, broken audio, or finalization timeout is observed.

L3 must remain a single-audio-source milestone. Dual-source mixing is validated separately in L4.
