# Troika D Lite — Mini Product Specification v0.1

## 1. Product definition

Troika D Lite is a minimal Linux screen recorder with one primary job:

> Record the full screen and optionally record microphone audio, system audio, or both, producing a usable video file.

It is not merely Troika D with buttons hidden. It is a separate product with a deliberately constrained scope.

Core product rule:

> **Open → choose audio → Record → Stop**

Every feature and implementation decision must justify itself against that rule.

## 2. Product goals

Troika D Lite must be:

- simple;
- lightweight;
- reliable;
- fast to start;
- easy to maintain;
- Linux-native;
- suitable for older or resource-constrained computers;
- free and open-source under GPL-3.0-or-later.

## 3. Required recording matrix

The first release must support exactly these four audio combinations:

| Microphone | System audio | Output |
| --- | --- | --- |
| OFF | OFF | screen video only |
| ON | OFF | screen video + microphone |
| OFF | ON | screen video + system audio |
| ON | ON | screen video + mixed microphone and system audio |

## 4. Video scope

Source:

- **Full Screen only**.

Not included:

- Window capture;
- Area capture;
- Active Window;
- crop/region selection.

Output:

- MP4 container;
- H.264 video.

Frame rates:

- 15 FPS;
- 30 FPS.

Default:

- 30 FPS.

60 FPS is explicitly out of scope for v0.1.

Native screen resolution is used unless field evidence later shows a strong reason to change this.

## 5. Audio scope

User controls:

- Record microphone: ON/OFF.
- Record system audio: ON/OFF.

Microphone selection may be exposed when multiple usable devices are present.

System audio should use the appropriate default monitor/source unless a real field requirement proves that multiple system-audio choices are needed.

When both audio inputs are enabled, they are mixed into the output audio track.

## 6. Pointer

The mouse pointer is included by default and permanently in v0.1.

No pointer ON/OFF control is needed unless a future user requirement justifies it.

## 7. User interface

The interface must stay small.

Target idle UI:

```text
┌───────────────────────────────┐
│        Troika D Lite          │
│                               │
│  ☑ Microphone                 │
│     [ Default microphone ▼ ]  │
│                               │
│  ☑ System audio               │
│                               │
│  Frame rate:                  │
│  ○ 15 FPS   ● 30 FPS          │
│                               │
│       ● Start Recording       │
└───────────────────────────────┘
```

Target recording UI:

```text
┌───────────────────────────────┐
│        Recording 00:03:27     │
│                               │
│          ■ Stop               │
└───────────────────────────────┘
```

No large Settings screen is part of v0.1.

## 8. Output

Default directory:

```text
~/Videos
```

File names must be timestamped and collision-safe, for example:

```text
TroikaD-Lite_2026-09-24_14-32-18.mp4
```

Existing files must never be overwritten silently.

## 9. Start / cancel behavior

Start Recording must:

1. request the Wayland screen stream through XDG Desktop Portal when required;
2. begin the media pipeline only after a valid authorized stream exists;
3. treat Portal cancellation as a normal user action;
4. not show an error dialog merely because the user selected Cancel.

## 10. Stop / finalization behavior

Stop must:

1. request clean EOS;
2. allow the muxer to finalize the file;
3. use a bounded timeout to avoid indefinite hangs;
4. preserve a playable output whenever practical;
5. clean up Portal, PipeWire, and GStreamer resources.

Do not remove bounded finalization safety merely to pursue theoretically perfect EOS behavior.

## 11. First target platform

Primary target:

```text
Ubuntu 24.04
Wayland
XDG Desktop Portal
PipeWire
```

X11 is not claimed as supported until field-tested.

The architecture may leave room for future X11 support, but v0.1 must not absorb major complexity for unvalidated X11 requirements.

## 12. Technical direction

UI:

- GTK.

Capture:

- XDG Desktop Portal;
- PipeWire.

Media pipeline:

- GStreamer.

Conceptual video path:

```text
PipeWire Screen
      ↓
conversion / rate control
      ↓
H.264 encoder
      ↓
                    ┐
                    │
Mic ────────────┐   │
                ├───┼→ MP4 mux → File
System audio ───┘   │
                    │
────────────────────┘
```

The implementation should use the smallest pipeline that remains stable and field-acceptable.

## 13. Proven Troika D concepts eligible for selective reuse

Only the minimum proven pieces should be considered for derivation:

- Wayland Portal ScreenCast session handling;
- PipeWire Full Screen capture;
- microphone discovery;
- system-audio discovery;
- audio mixing;
- Full Screen GStreamer path;
- H.264 / MP4 path;
- EOS/finalization logic;
- clean Portal cancellation semantics;
- resource cleanup;
- desktop integration patterns;
- Debian packaging lessons;
- CI lessons.

Selective reuse does not mean copying entire Troika D modules unchanged.

## 14. Explicitly excluded from v0.1

Do not add:

- Window capture;
- Area capture;
- Area preview;
- crop geometry;
- Webcam;
- Camera discovery;
- Camera compositor;
- Screenshot;
- Screenshot Portal;
- Pause/Resume;
- 60 FPS;
- Economy/High/Quality profiles;
- Window PERF-001 logic;
- PERF-002 experimental work;
- editor;
- effects;
- streaming;
- global shortcuts;
- countdown.

## 15. Performance requirement

Lightweight behavior is a product requirement.

Before the first release, measure at least:

- CPU usage;
- RSS memory;
- recording smoothness;
- dropped/duplicated frames where measurable;
- startup time;
- finalization time.

Measure 15 FPS and 30 FPS across the four required audio combinations.

A feature that materially increases resource consumption must justify that cost.

## 16. Acceptance criteria

Technical success alone is insufficient.

A release candidate must produce:

- playable output;
- visually acceptable recording;
- synchronized audio;
- no unexplained green corruption;
- no checkerboard startup/end artifacts;
- no unacceptable stutter;
- reliable Stop/finalization;
- clean Portal Cancel behavior.

Human field validation is required for changes affecting the recording pipeline.

## 17. Core test matrix

The deliberate v0.1 matrix is:

```text
2 frame rates
×
2 microphone states
×
2 system-audio states
=
8 primary cases
```

All eight cases should be practical to test for every release candidate.

## 18. Distribution

Initial distribution targets:

- GitHub source;
- native `.deb`.

A user-local installer may be included if it remains simple and useful.

AppImage and Flatpak are not v0.1 requirements.

## 19. Scope-creep rule

Before adding any new feature, answer:

> Is this necessary for “full-screen recording + optional microphone/system audio”?

If the answer is no, it does not enter the core v0.1 product.

## 20. v0.1 success definition

Troika D Lite v0.1 succeeds when the user can reliably:

```text
Open
↓
select microphone/system audio state
↓
select 15 or 30 FPS
↓
Record
↓
record the full screen smoothly enough for practical use
↓
Stop
↓
receive a valid MP4
```

## 21. Product philosophy

Troika D Lite is not “Troika D with fewer features.”

It is:

> **A minimal, dependable screen-and-audio recorder for Linux.**

Its value is doing one job very well with the smallest reasonable complexity.
