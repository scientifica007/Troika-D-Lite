# L4 Field Test — 2026-09-25

## Tested builds

Initial dual-audio runtime commit:

```
fa6832d3eed84933de9b62642347ed8e4549fddc
```

Portal reentrancy fix commit:

```
db400b833457321ae773b915c3853fee4e26ec34
```

Target environment: Ubuntu 24.04 / Wayland.

## Human acceptance result

The L4 media gate and the focused follow-up gate passed on 2026-09-25.

The complete eight-case v0.1 matrix was reported successful:

| FPS | Microphone | System audio | Result |
| --- | --- | --- | --- |
| 15 | OFF | OFF | PASS |
| 15 | ON | OFF | PASS |
| 15 | OFF | ON | PASS |
| 15 | ON | ON | PASS |
| 30 | OFF | OFF | PASS |
| 30 | ON | OFF | PASS |
| 30 | OFF | ON | PASS |
| 30 | ON | ON | PASS |

Dual-audio recordings contained both microphone and system playback, remained usable and synchronized, and did not report pipeline fallback or finalization timeout.

## Representative dual-audio evidence

```text
EOS request: source-pads=[screen_src:1,mic_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=1 system=1 in=596 out=370 drop=267 duplicate=41

EOS request: source-pads=[screen_src:1,mic_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=1 system=1 in=515 out=626 drop=26 duplicate=137
```

Additional successful dual-audio runs after the reentrancy fix included:

```text
EOS request: source-pads=[screen_src:1,mic_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=1 system=1 in=489 out=298 drop=215 duplicate=24

EOS request: source-pads=[screen_src:1,mic_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=1 system=1 in=222 out=783 drop=11 duplicate=572
```

No `pipeline-fallback=1`, `Recording error`, or `finalize-timeout` was reported in the L4 dual-audio test sequence.

## Portal reentrancy defect and fix

Initial field testing found that repeated presses of **Start Recording** while the system Share Screen dialog was already open could create additional Portal dialogs.

The root cause was application reentrancy during the nested GLib loop used while waiting for the Portal response.

Fix commit:

```
db400b833457321ae773b915c3853fee4e26ec34
```

The fix introduced:

- a Recorder `starting/busy` state;
- Start rejection while a Portal request is pending;
- disabled Start/FPS/audio controls during pending screen selection;
- suspended idle audio-device polling while pending;
- safe handling of application-window close while the Portal dialog is unresolved.

Focused retesting confirmed:

- repeated Start activation no longer creates multiple Share Screen dialogs;
- Cancel returns controls to a usable state;
- a subsequent Start creates exactly one new Portal dialog.

**Portal reentrancy fix: PASS.**

## Audio interruption observation

Initial L4 testing reported a very brief, subtle audio interruption on some workspace switches when the machine appeared to be under heavier load.

Focused retesting after the reentrancy fix reported no continuing audio problem.

No GStreamer error, pipeline fallback, or finalization timeout had accompanied the original observation.

The observation is retained as performance evidence rather than classified as an L4 media defect. It can be revisited during controlled performance benchmarking if it reappears.

## System Portal text-rendering observation

The system **Share Screen** dialog continues to show partially erased/corrupted text in the test environment even after the application reentrancy defect was fixed and only one Portal dialog is present.

Important boundary:

- the affected text belongs to the desktop Portal UI;
- Troika D Lite does not render the Share Screen dialog;
- the artifact persists with a single Portal request;
- screen selection remains functional;
- recording behavior is unaffected.

Therefore this is recorded as an **external/system UI rendering observation**, not as an L4 application-blocking defect.

No application workaround is introduced without evidence that Troika D Lite causes or can reliably mitigate the compositor/Portal rendering artifact.

## Videorate diagnostics

The collected `drop` and `duplicate` counters remain diagnostic baseline data only.

They do not override the successful human visual/audio acceptance result. They should be analyzed under controlled workloads during the dedicated performance milestone.

## L4 decision

**L4 HUMAN FIELD GATE: PASS**

L4 completes the functional v0.1 audio-state matrix:

- video only;
- microphone only;
- system audio only;
- microphone + system audio;

at both 15 FPS and 30 FPS.

The remaining Share Screen text-rendering artifact is documented as a non-blocking external/system observation.
