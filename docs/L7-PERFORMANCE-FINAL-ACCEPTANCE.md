# L7 — Performance benchmark and final field acceptance

## Purpose

L7 measures the accepted product rather than adding features.

The goals are:

1. quantify Troika D Lite resource use on the field machine;
2. compare it with Troika D under controlled, like-for-like settings;
3. verify finalization behavior and videorate diagnostics under repeatable workloads;
4. perform the final field acceptance before a beta release decision.

L7 must not tune the accepted media pipeline merely to improve benchmark numbers. Any optimization requires a reproducible problem and a separate before/after field check.

## Reference revisions

L7 begins from:

- Troika D Lite `main`: `00a6ee0d555c4c46b0681fa544588fd44cd2718b`
- Troika D reference `main`: `cb19f06483c3f3e1641cac025a7683094d839dec`

The Troika D reference is read-only for this comparison.

## Controlled encoder equivalence

Troika D Lite uses:

- H.264/x264;
- 4500 kb/s;
- `veryfast`;
- key interval 60.

Troika D's **Balanced** profile uses the same 4500 kb/s / `veryfast` encoder baseline.

Therefore controlled comparison runs must use **Balanced** in Troika D and the same FPS/audio state in both applications.

## Benchmark harness

`scripts/benchmark_session.py` launches either application and records:

- application startup proxy: process launch to ownership of its GTK application D-Bus name;
- idle CPU mean/peak;
- idle RSS mean/peak;
- recording CPU mean/peak;
- recording RSS mean/peak;
- finalization time: `EOS request` log timestamp to normal EOS/finalization log timestamp;
- finalization outcome;
- existing videorate timing line.

CPU is process CPU and may exceed 100% when multiple cores are used.

RSS is the main recorder process resident set. GStreamer encoding/muxing runs in that process. Very short helper processes used for device discovery are intentionally not folded into RSS.

The harness does not alter the recorder pipeline.

## Performance plan

Use the same machine, desktop session, monitor, output directory, pointer state, source devices, and workload discipline.

L7 has two layers so that the v0.1 specification is fully measured without turning the field gate into dozens of unnecessary repetitions.

### Layer 1 — complete Lite performance matrix

Measure Troika D Lite once for each required FPS/audio combination:

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

Use a 30-second measured recording window for this coverage sweep.

This satisfies the product requirement to measure 15 FPS and 30 FPS across all four required audio states.

For consistency:
- use the low-motion workload for video-only and single-audio cases;
- use the same local playback plus ordinary desktop motion for dual-audio cases;
- keep the microphone, default output, power state, monitor resolution, and desktop session unchanged.

The preferred field runner is:

```bash
cd ~/Troika-D-Lite

python3 scripts/run_lite_matrix.py
```

It runs the eight cases sequentially with a 10-second idle sample and 30-second recording sample. Before every case it prints the required FPS/audio state and waits for Enter. It is resume-safe: a case that already has a successful EOS JSON under `benchmark-results/lite-matrix/` is skipped unless `--rerun-completed` is supplied.

Do not configure the application during the idle measurement. Wait until the per-session benchmark prints its configuration prompt, then set the stated controls and press Start/Share.

### Layer 2 — controlled repeated comparison with Troika D

Use two representative scenarios and run each **three times per application**.

#### Scenario A — low-resource baseline

- Full Screen;
- 15 FPS;
- microphone OFF;
- system audio OFF;
- low-motion desktop;
- 60-second measured recording window.

#### Scenario B — high-load representative use

- Full Screen;
- 30 FPS;
- microphone ON;
- system audio ON;
- Troika D: Balanced profile;
- same microphone;
- same default system-audio sink;
- same high-motion local playback/workload;
- 60-second measured recording window.

Preferred Layer 2 runner:

```bash
cd ~/Troika-D-Lite
python3 scripts/run_controlled_comparison.py
```

It validates pinned revisions, alternates application order, resumes successful runs, prints the required UI configuration, and generates the summary after all repetitions.

Layer 2 produces 12 measured sessions:

```text
2 scenarios × 2 applications × 3 repetitions = 12
```

Together with the eight-case Lite coverage sweep, the planned L7 measurement set is 20 sessions.

The already accepted L4 matrix remains the functional baseline; L7 adds quantitative resource measurements rather than re-litigating functionality.

## Layer 1 field status

**PASS — 2026-09-25.**

All eight required Lite FPS/audio combinations were measured and all finalized through normal EOS. Aggregate evidence is recorded in `docs/FIELD-TEST-L7-2026-09-25.md`.

## Workload discipline

For Scenario A, leave the selected desktop mostly static.

For Scenario B, use the same locally stored moving video or other deterministic high-motion workload for both applications. Avoid network-stream variability if possible.

Do not compare a quiet desktop in one application against active scrolling/video in the other.

Close unrelated heavy applications when practical and keep power mode, charger state, monitor resolution, and desktop session unchanged across the comparison.

## Running one session

Example for Troika D Lite from source:

```bash
cd ~/Troika-D-Lite

python3 scripts/benchmark_session.py \
  --app lite \
  --scenario A-15-video-low \
  --fps 15 \
  --mic 0 \
  --system-audio 0 \
  --workload low \
  --app-id io.github.scientifica007.TroikaDLite \
  --cwd "$HOME/Troika-D-Lite" \
  --output-dir "$HOME/Videos" \
  -- \
  env PYTHONPATH=src /usr/bin/python3 -m troika_d_lite
```

Example for Troika D:

```bash
cd ~/Troika-D-Lite

python3 scripts/benchmark_session.py \
  --app troika-d \
  --scenario A-15-video-low \
  --fps 15 \
  --mic 0 \
  --system-audio 0 \
  --workload low \
  --app-id io.github.scientifica007.TroikaD \
  --cwd "$HOME/Troika-D" \
  --output-dir "$HOME/Videos" \
  -- \
  env PYTHONPATH=src /usr/bin/python3 -m ubuntu_screen_recorder
```

The script:

1. refuses to benchmark an already-running instance;
2. measures D-Bus startup ownership;
3. samples 10 seconds of idle CPU/RSS;
4. waits for a new media file to identify recording start;
5. samples 60 seconds of recording load;
6. notifies the user to click Stop;
7. measures EOS finalization from existing logs;
8. stores JSON + raw application log under `benchmark-results/`;
9. closes the benchmark-launched application after the recording is safely finalized.

## Summarizing repetitions

After the runs:

```bash
python3 scripts/summarize_benchmarks.py \
  benchmark-results/*.json \
  --require-lite-matrix \
  --json-out benchmark-results/summary.json
```

The command fails if any of the eight required Lite FPS/audio combinations is missing. The table reports medians grouped by application and scenario.

Raw JSON/log files under `benchmark-results/` remain local because they contain machine-specific paths and diagnostic detail. The repository should receive the aggregate numeric table, benchmark conditions, interpretation, and final field conclusion in the L7 field-test document.

## Benchmark harness field smoke

The benchmark harness itself passed a target-machine smoke test on 2026-09-25 using 15 FPS, microphone OFF, system audio OFF, low-motion workload.

Observed smoke values:

| Metric | Value |
| --- | ---: |
| Startup proxy | 327.958 ms |
| Idle CPU mean | 10.586% |
| Idle RSS mean | 64.472 MiB |
| Recording CPU mean | 61.081% |
| Recording RSS mean | 112.126 MiB |
| Recording RSS peak | 114.656 MiB |
| Finalization | 575.307 ms |
| Finalization outcome | EOS |

No pipeline fallback or finalization timeout was reported. This smoke result validates the measurement workflow; it is not used as one of the formal eight matrix cases.

## Interpretation rules

No single metric is sufficient.

Review together:

- CPU;
- RSS;
- startup proxy;
- finalization;
- videorate diagnostics;
- human smoothness;
- audio continuity/sync;
- presence or absence of timeouts/errors.

`drop` and `duplicate` counts remain diagnostics, not standalone quality verdicts. The field tests already established that visually acceptable recordings can contain substantial videorate adaptation on this machine.

A one-off finalization timeout must be logged. Repeated timeout behavior is a release blocker until investigated.

## Layer 2 field status

**MEASUREMENTS COMPLETE — 2026-09-25.**

All 12 controlled runs completed through normal EOS.

Scenario B shows essentially equivalent recording CPU with modestly lower Lite RSS.

Scenario A shows a reproducible large Lite CPU disadvantage in the low-motion video-only condition. Exact pipeline review does not reveal a material Full Screen chain difference, while Lite's visible one-second recording timer creates compositor changes that Troika D does not.

The focused hidden-window probe confirmed the hypothesis: Lite CPU fell from the prior visible-window median of 41.685% to 17.209%, effectively matching Troika D's 17.139% median. The live elapsed-time label is therefore removed as a minimal product-performance correction.

The corrected static recording view was rechecked three times with the Lite window visible normally.

The corrected Scenario A median recording CPU is 2.896%, versus 41.685% before the correction. All three runs finalized through normal EOS.

**Low-motion CPU regression: CLOSED / PASS.**

The corrected low-motion finalization median is 5.929 s, with all three runs below the 12-second bounded timeout. This is retained as a non-blocking observation and must be considered alongside the final installed-package high-load run.

Detailed medians and interpretation are recorded in `docs/FIELD-TEST-L7-2026-09-25.md`.

## Final installed-package run status

The current-head Debian package `0.1.0~alpha0-2` completed an approximately 5 min 45 s 30 FPS microphone+system-audio recording and stopped through clean source-level EOS with no fallback/timeout/error.

A media interruption was observed only during a period when the desktop itself became visibly overloaded while switching workspaces during local-video playback. YouTube playback plus workspace switching did not reproduce the issue.

The focused workload-isolation check reproduced the same local-video/workspace-switch host stutter with **no recorder running**.

That result resolves the observation as an environment/video-player/compositor capacity condition rather than a Lite-specific recorder defect.

A separate Troika D stress reproduction is no longer required for this classification.

## Final field acceptance

After the benchmark, perform one final installed-package recording using the L6 package path:

- 30 FPS;
- microphone + system audio;
- at least 2–3 minutes;
- normal Stop;
- visually inspect motion;
- listen for audio continuity and sync from beginning to end;
- confirm the MP4 opens normally;
- confirm no green/checkerboard corruption;
- confirm no finalization timeout.

The known partially erased text in the desktop Share Screen Portal remains an external/system rendering observation unless new evidence connects it to Troika D Lite.

## L7 acceptance gate

**PASS — 2026-09-25.**

Validated:

- benchmark tooling passes CI;
- all eight Lite FPS/audio combinations have performance measurements;
- three repetitions exist for each application/scenario pair in the two controlled comparison scenarios;
- measurements are internally consistent enough to interpret;
- the only reproducible Lite-specific performance regression found was the live recording timer; it was removed and the corrected visible-window Scenario A recheck passed;
- no repeated finalization timeout appears;
- the current-head installed Debian package completed a long 30 FPS microphone+system-audio recording through clean EOS;
- the local-video/workspace-switch stutter reproduces without any recorder and is classified as an external host/video-player/compositor saturation condition;
- benchmark results and the field conclusion are committed to the repository.

**L7 FINAL FIELD GATE: PASS.**

L7 reports measured differences. It does not require Troika D Lite to win every metric. The product goal is materially lower complexity with dependable performance on the target machine.

## After L7

A beta release decision is a separate release milestone. L7 acceptance does not automatically publish or tag a release.
