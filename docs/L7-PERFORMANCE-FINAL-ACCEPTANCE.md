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

## Controlled benchmark scenarios

Use the same machine, desktop session, monitor, output directory, pointer state, source devices, and workload.

Run each scenario **three times per application** and compare medians.

### Scenario A — low-resource baseline

- Full Screen;
- 15 FPS;
- microphone OFF;
- system audio OFF;
- low-motion desktop;
- 60-second measured recording window.

### Scenario B — high-load representative use

- Full Screen;
- 30 FPS;
- microphone ON;
- system audio ON;
- Troika D: Balanced profile;
- same microphone;
- same default system-audio sink;
- same high-motion local playback/workload;
- 60-second measured recording window.

This produces 12 measured sessions total:

```text
2 scenarios × 2 applications × 3 repetitions = 12
```

The already accepted L4 eight-case matrix remains the functional coverage. L7 does not repeat all eight cases three times merely to generate performance statistics.

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
  --json-out benchmark-results/summary.json
```

The table reports medians grouped by application and scenario.

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

L7 passes when:

- benchmark tooling passes CI;
- three repetitions exist for each application/scenario pair;
- measurements are internally consistent enough to interpret;
- no reproducible recorder regression appears;
- no repeated finalization timeout appears;
- final installed-package 2–3 minute dual-audio recording passes;
- benchmark results and field conclusion are committed to the repository.

L7 reports measured differences. It does not require Troika D Lite to win every metric. The product goal is materially lower complexity with dependable performance on the target machine.

## After L7

A beta release decision is a separate release milestone. L7 acceptance does not automatically publish or tag a release.
