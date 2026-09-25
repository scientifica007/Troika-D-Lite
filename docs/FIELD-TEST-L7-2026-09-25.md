# L7 Field Test — 2026-09-25

## Status

L7 is in progress.

Completed:

- benchmark harness target-machine smoke: PASS;
- complete eight-case Troika D Lite performance sweep: PASS;
- all eight matrix runs finalized through normal EOS;
- no pipeline fallback reported;
- no finalization timeout reported.

Pending:

- controlled repeated Troika D Lite vs Troika D comparison;
- final installed-package 2–3 minute 30 FPS dual-audio acceptance run;
- final L7 interpretation and acceptance decision.

## Field environment

Target: Ubuntu 24.04 / Wayland on the project field machine.

Raw benchmark JSON/log files remain local under `benchmark-results/`. This document records aggregate, non-private evidence.

## Benchmark harness smoke

| Metric | Value |
| --- | ---: |
| Startup proxy | 327.958 ms |
| Idle CPU mean | 10.586% |
| Idle RSS mean | 64.472 MiB |
| Recording CPU mean | 61.081% |
| Recording RSS mean | 112.126 MiB |
| Recording RSS peak | 114.656 MiB |
| Finalization | 575.307 ms |
| Outcome | EOS |

**Harness smoke: PASS.**

## Lite eight-case performance matrix

| Scenario | Startup ms | Idle CPU % | Idle RSS MiB | Record CPU % | Record RSS MiB | Peak RSS MiB | Finalize ms | Outcome |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 15 FPS / video only / low | 326.717 | 3.495 | 65.580 | 43.523 | 112.930 | 115.938 | 595.592 | EOS |
| 15 FPS / system / low | 324.015 | 11.082 | 66.935 | 43.491 | 143.739 | 145.934 | 406.404 | EOS |
| 15 FPS / mic / low | 327.497 | 9.686 | 66.567 | 49.053 | 143.995 | 145.242 | 283.493 | EOS |
| 15 FPS / mic+system / high | 3967.755 | 16.373 | 63.423 | 119.802 | 141.581 | 146.992 | 258.288 | EOS |
| 30 FPS / video only / low | 897.990 | 22.466 | 76.731 | 75.100 | 112.446 | 112.480 | 204.958 | EOS |
| 30 FPS / system / low | 322.970 | 37.710 | 102.087 | 72.880 | 143.786 | 143.809 | 222.287 | EOS |
| 30 FPS / mic / low | 326.426 | 13.876 | 67.116 | 91.787 | 143.643 | 145.188 | 371.020 | EOS |
| 30 FPS / mic+system / high | 326.834 | 57.816 | 97.672 | 146.292 | 145.176 | 149.141 | 306.138 | EOS |

**Lite eight-case performance coverage: COMPLETE / PASS.**

## Matrix interpretation

All eight cases ended through normal EOS. Finalization ranged from about 205 ms to 596 ms; the median is about 295 ms.

Video-only recording RSS was about 112 MiB. Single-audio cases were generally about 144 MiB. This single-run sweep therefore shows roughly 30 MiB higher recorder RSS when an audio path is active, but it is descriptive rather than a repeated causal estimate.

For low-motion runs, 15 FPS video-only/single-audio cases were about 43–49% mean process CPU and 30 FPS cases about 73–92%.

The dual-audio cases used the HIGH workload, so their higher CPU figures cannot be attributed to mixing alone.

Most startup measurements cluster near 323–327 ms. The 3967.755 ms and 897.990 ms observations are clear one-run outliers. Several later idle measurements are also higher than the early baseline. They are retained as evidence but are not classified as regressions without repetition.

No pipeline tuning is justified from this matrix alone.

## Controlled comparison

The next stage uses:

- Scenario A: 15 FPS, video-only, low motion;
- Scenario B: 30 FPS, microphone + system audio, high motion.

Each app/scenario pair is repeated three times and interpreted using medians.

Pinned references:

- Lite runtime baseline: `00a6ee0d555c4c46b0681fa544588fd44cd2718b`;
- Troika D reference: `cb19f06483c3f3e1641cac025a7683094d839dec`.

The comparison runner refuses a changed Lite `src/`, a mismatched Troika D commit, or local Troika D `src/` changes.

## Interim decision

**Layer 1: PASS.**

L7 remains open pending Layer 2 and the final installed-package run.


## Layer 2 — controlled repeated comparison

The complete 12-session comparison finished successfully.

All four app/scenario groups contain three successful EOS runs.

| Scenario | App | Startup ms | Idle CPU % | Idle RSS MiB | Record CPU % | Record RSS MiB | Peak RSS MiB | Finalize ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A — 15 FPS video-only low | Lite | 334.836 | 10.781 | 66.828 | 41.685 | 112.388 | 114.664 | 487.754 |
| A — 15 FPS video-only low | Troika D | 326.110 | 10.277 | 67.378 | 17.139 | 114.308 | 116.051 | 2747.759 |
| B — 30 FPS dual-audio high | Lite | 325.550 | 10.683 | 66.645 | 150.798 | 144.676 | 148.621 | 353.855 |
| B — 30 FPS dual-audio high | Troika D | 326.960 | 24.654 | 68.650 | 148.157 | 148.488 | 152.219 | 377.213 |

Every run finalized through normal EOS.

### Scenario A interpretation

Startup medians are effectively similar at this scale.

Lite mean recording RSS is about 1.9 MiB lower (~1.7%) and peak RSS about 1.4 MiB lower (~1.2%).

Lite finalization median is about 2.26 seconds faster (~82%).

However, Lite recording CPU is much higher: 41.685% vs 17.139%, approximately 143% higher relative to Troika D.

This CPU difference is large enough to investigate before final L7 acceptance because low-resource behavior is a primary Lite objective.

### Scenario B interpretation

Startup medians are effectively identical.

Lite idle CPU is lower by about 14 percentage points (~57%), and idle RSS lower by about 2.0 MiB (~2.9%).

Recording CPU is effectively similar: Lite is about 1.8% higher.

Lite recording RSS is about 3.8 MiB lower (~2.6%) and peak RSS about 3.6 MiB lower (~2.4%).

Lite finalization median is about 23 ms faster (~6.2%).

### Full-screen pipeline comparison

A source review of the exact benchmark revisions found no material difference in the Full Screen video pipeline capable of explaining Scenario A by itself.

Both use the same effective chain:

`pipewiresrc -> queue -> videoconvert/I420 -> videorate -> videoscale -> x264enc 4500/veryfast -> h264parse -> mp4mux`.

### Low-motion UI-damage hypothesis

The applications differ in one relevant visible behavior:

- Lite updates a live elapsed-time label once per second while recording;
- Troika D has no equivalent live recording timer.

Because the selected source is the complete screen, the recorder window itself is part of the captured compositor output when visible.

The videorate input counters support the hypothesis that the two “low-motion” runs were not equivalent at the compositor-damage level:

- representative Lite Scenario A inputs were substantially above the Troika D inputs;
- Troika D commonly received only about 32–34 real PipeWire frames in the 60-second interval, while Lite received substantially more real input frames.

The target output FPS is still produced by videorate duplication, but processing more real changing full-screen frames can materially increase conversion/encoding work.

This is a strong hypothesis, not yet a proven root cause.

### Layer 2 status

**CONTROLLED REPETITIONS: COMPLETE.**

**PERFORMANCE INTERPRETATION: OPEN — focused low-motion UI-visibility probe required.**

No pipeline change is justified. The next test isolates whether Lite's visible dynamic recording UI is responsible for the Scenario A CPU gap.


## Focused hidden-UI probe

A focused Lite-only probe repeated Scenario A while the dynamic Troika D Lite recording window was not visible on the captured active workspace for the measured interval.

Observed:

| Metric | Hidden-UI probe |
| --- | ---: |
| Startup proxy | 328.528 ms |
| Idle CPU mean | 5.489% |
| Idle RSS mean | 65.664 MiB |
| Recording CPU mean | 17.209% |
| Recording RSS mean | 112.600 MiB |
| Recording RSS peak | 112.867 MiB |
| Finalization | 3041.032 ms |
| Outcome | EOS |
| Videorate | in=82, out=938, drop=26, duplicate=882 |

The CPU result is decisive for the performance question:

- previous Lite Scenario A controlled median with visible live timer: 41.685%;
- hidden-UI probe: 17.209%;
- Troika D Scenario A controlled median: 17.139%.

The hidden-UI Lite result is within approximately 0.4% relative of Troika D's CPU median.

This strongly confirms that the Scenario A CPU gap was caused by self-generated visible compositor activity from Lite's once-per-second elapsed-time UI, not by the accepted GStreamer Full Screen pipeline.

The hidden probe's 3.041 s finalization is retained as a one-run timing outlier. It still ended through normal EOS and does not overturn the broader finalization evidence.

## L7 performance correction

The live elapsed-time label is removed from the recording view.

The static Recording state, FPS/audio summary, and Stop button remain.

Reason:

- elapsed time is not a v0.1 product requirement;
- the field probe demonstrates a material low-motion CPU cost when the changing label is visible inside a Full Screen capture;
- removing the dynamic label directly addresses the proven cause without modifying the media pipeline, codecs, buffering, or Portal behavior.

A three-run visible-window Scenario A recheck is required after this change before the performance finding can be closed.


## Corrected visible-window Scenario A recheck

After removing the live elapsed-time UI, Scenario A was repeated three times with the Troika D Lite recording window visible normally on the captured desktop.

Results:

| Run | Startup ms | Idle CPU % | Idle RSS MiB | Record CPU % | Record RSS MiB | Peak RSS MiB | Finalize ms | Outcome | Videorate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 392.635 | 7.589 | 66.284 | 2.896 | 112.172 | 112.414 | 8752.001 | EOS | in=37 out=936 drop=16 duplicate=915 |
| 2 | 360.595 | 4.192 | 65.501 | 2.163 | 112.026 | 113.070 | 5929.024 | EOS | in=60 out=936 drop=29 duplicate=905 |
| 3 | 363.298 | 4.494 | 65.471 | 12.605 | 112.248 | 112.609 | 5515.601 | EOS | in=47 out=935 drop=21 duplicate=909 |

Median summary:

| Metric | Corrected Lite median |
| --- | ---: |
| Startup | 363.298 ms |
| Idle CPU | 4.494% |
| Idle RSS | 65.501 MiB |
| Recording CPU | 2.896% |
| Recording RSS | 112.172 MiB |
| Recording RSS peak | 112.609 MiB |
| Finalization | 5929.024 ms |
| Finalization outcome | EOS |

### CPU regression closure

The previously observed visible-window Lite Scenario A CPU median was 41.685%.

After the timer correction, the visible-window median is 2.896%.

This is a reduction of approximately 93% relative to the pre-correction Lite median.

The corrected value is also well below the earlier Troika D Scenario A median of 17.139%. This should not be generalized as a universal Lite advantage because low-motion CPU is highly sensitive to compositor damage and desktop activity. It does establish that the earlier Lite-specific CPU regression is closed.

The corrected videorate input counts (37, 60, 47) are much closer to the quiet-screen behavior observed in Troika D than the pre-correction Lite runs, further supporting the self-generated UI-damage diagnosis.

**Low-motion CPU regression: CLOSED / PASS.**

### Finalization observation after correction

All three corrected runs finalized through normal EOS with no pipeline fallback or timeout.

Finalization times were 8.752 s, 5.929 s, and 5.516 s.

These are materially slower than the earlier visible-timer Lite medians, but remain below the 12-second bounded finalization timeout and are not release-blocking by themselves.

The final installed-package 30 FPS dual-audio run remains required to confirm practical finalization behavior under the representative high-load use case.

## L7 status after performance correction

- Layer 1 matrix: PASS;
- Layer 2 controlled comparison: COMPLETE;
- hidden-UI root-cause probe: PASS;
- live-timer correction: implemented;
- corrected visible-window Scenario A recheck: PASS;
- low-motion CPU regression: CLOSED;
- final installed-package 2–3 minute dual-audio acceptance: PENDING.


## Final installed-package high-load run

Package:

```text
Status: install ok installed
Version: 0.1.0~alpha0-2
```

The package was built from the current L7 branch after the live-timer performance correction.

Configuration:

- 30 FPS;
- microphone ON;
- system audio ON;
- installed `troika-d-lite` command;
- local moving-video playback;
- desktop/workspace switching during the run.

Recorder shutdown evidence:

```text
EOS request: source-pads=[screen_src:1,mic_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=1 system=1 in=5204 out=10347 drop=264 duplicate=5407
```

Output file:

```text
~/Videos/TroikaD-Lite_2026-09-25_15-27-12.mp4
313 MiB
```

The `out=10347` counter at 30 FPS corresponds to roughly 345 seconds (~5 min 45 s) of output-frame time, so this run materially exceeded the requested 2–3 minute acceptance duration.

No `pipeline-fallback=1`, `finalize-timeout`, or `Recording error` was reported.

### Stress observation

During one portion of the local-video workload, repeated workspace switching caused the host desktop itself to become visibly overloaded:

- pointer movement became intermittent/stalled;
- general desktop interaction became heavy;
- the recorded video showed a corresponding interruption in both motion and audio.

When the user remained on the workspace playing the local video, recording was normal.

A separate YouTube playback test with page movement and workspace switching did **not** reproduce the problem.

This correlation matters: the observed capture degradation coincided with host/compositor responsiveness degradation rather than occurring while the desktop remained responsive.

### Current classification

**Installed-package recorder lifecycle: PASS.**

**Media quality under ordinary/high workload: PASS where the host remains responsive.**

**Extreme local-video + workspace-switch condition: CLASSIFICATION HOLD.**

The evidence currently favors a host-resource/compositor saturation explanation because mouse/desktop responsiveness degraded at the same moment as the recording. It is not yet sufficient to declare the recorder itself defective or to dismiss the observation as purely environmental.

One focused classification check remains: reproduce the same local-video/workspace-switch workload (1) with no recorder and (2) with the pinned Troika D reference. This distinguishes host/video-player saturation from a Lite-specific interaction.
