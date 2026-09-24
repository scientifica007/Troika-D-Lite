# L1 — Full-screen video-only vertical slice

## Purpose

L1 proves the smallest real Troika D Lite recording path before any audio code is introduced.

The supported L1 workflow is:

Open → choose 15 or 30 FPS → Start → approve one complete monitor in the Wayland portal → record → Stop → receive MP4/H.264.

L1 is intentionally not the full v0.1 product. Microphone and system audio arrive in later milestones.

## Runtime modules

The L1 runtime is deliberately limited to four substantive modules:

- app.py — tiny GTK3 user interface and output naming.
- portal.py — XDG ScreenCast session lifecycle only.
- pipeline.py — full-screen PipeWire to H.264/MP4 pipeline only.
- recorder.py — start, stop, EOS, bounded finalization, bus handling, and cleanup.

There is no models.py, geometry.py, system_probe.py, audio.py, camera module, screenshot module, or X11 backend in L1.

## Selective derivation from Troika D

Troika D main was reviewed before implementation. L1 preserves only field-proven behavior relevant to Lite:

- CreateSession / SelectSources / Start / OpenPipeWireRemote.
- monitor-only selection with the pointer embedded.
- pipewire-serial selection when available, with node-id fallback.
- the field-tested Full Screen ordering: PipeWire → bounded queue → videoconvert/I420 → videorate → requested FPS.
- x264/H.264 and MP4.
- robust periodic MP4 moov updates.
- source-level EOS with pipeline EOS fallback.
- bounded finalization.
- explicit Portal session and PipeWire fd cleanup.
- Session::Closed handling for system-side stop.
- GTK/GDK version pinning before GI imports.
- videorate in/out/drop/duplicate diagnostics.

The following Troika D paths are explicitly rejected from L1:

- X11/ximagesrc.
- Window and Active Window.
- Area preview/crop/geometry.
- Webcam/V4L2/compositor.
- Screenshot Portal.
- Pause/Resume.
- audio-only recording.
- microphone/system audio.
- VP8/WebM fallback.
- 60 FPS.
- quality profiles.

## Provisional internal encoding baseline

L1 uses one non-user-configurable software H.264 baseline:

- x264enc.
- bitrate: 4500 kb/s.
- speed preset: veryfast.
- tune: zerolatency.
- key-int-max: 60.

This is not a new user-facing quality profile. It is an implementation baseline that must be measured later against the product performance requirements.

## Stop/finalization

L1 starts with the current field-proven Troika D safety model rather than a theoretical redesign:

1. push EOS downstream from screen_src;
2. fall back to pipeline EOS if necessary;
3. wait for normal mux EOS;
4. enforce a 12-second upper bound;
5. keep robust MP4 index updates active;
6. close the Portal session and PipeWire file descriptor;
7. return the UI to idle.

The 12-second value is an initial baseline from the current Troika D implementation and remains subject to Lite field measurement.

## Acceptance gate

CI can validate structure and deterministic pipeline construction, but L1 is not accepted until a human field test on Ubuntu 24.04 Wayland confirms at least:

- 15 FPS video-only is playable and visually acceptable.
- 30 FPS video-only is playable and visually acceptable.
- Portal Cancel returns cleanly without an error dialog.
- Stop finalizes a playable MP4.
- closing the app while recording takes the safe Stop path.
- system-side screen-sharing stop does not leave the application or Portal session stuck.
- no green corruption, checkerboard corruption, or unacceptable stutter is observed.

A pipeline change that passes CI but fails this field gate is not accepted.
