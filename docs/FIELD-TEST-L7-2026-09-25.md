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
