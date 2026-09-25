# MIC-001 — microphone dropout diagnostic

Issue: #13

## Purpose

The published `v0.1.0-beta.1` has a field-reported release-blocking
microphone defect: repeated long dropouts occur with both internal and
external microphones, at both 15/30 FPS, and with system audio both OFF
and ON.

This diagnostic branch does **not** tune the media pipeline. It adds
observability only.

## In-app diagnostics

When microphone capture is active, the recorder prints:

- the selected pipeline clock;
- requested and actual Pulse buffer/latency values;
- the microphone source device;
- discontinuity flags on microphone buffers;
- timestamp gaps of 100 ms or more at the `mic_src` source pad;
- a final microphone timing summary;
- GStreamer CLOCK_LOST, QOS, LATENCY, and WARNING messages.

A timestamp gap at `mic_src` proves the interruption is already present
at the audio source boundary. Continuous source timestamps do not by
themselves prove audio samples are non-silent, so the standalone WAV
comparison below is also required.

## First reproduction

Run from this branch:

```bash
cd ~/Troika-D-Lite
git fetch origin
git switch hotfix/mic-001-diagnostics
git pull

PYTHONPATH=src /usr/bin/python3 -m troika_d_lite \
  2>&1 | tee /tmp/troika-lite-mic001.log
```

Use the simplest case first:

- 15 FPS;
- microphone ON;
- system audio OFF;
- internal microphone;
- speak continuously for 2–3 minutes;
- Stop normally.

Listen to the saved MP4 and confirm whether the long dropouts reproduce.

Then extract:

```bash
grep -E \
'Pipeline clock|Mic source config|MIC GAP|MIC DISCONT|Mic timing stats|CLOCK_LOST|QOS|LATENCY|WARNING|Recording error|EOS request' \
/tmp/troika-lite-mic001.log
```

## Standalone Pulse comparison

Run:

```bash
cd ~/Troika-D-Lite
bash scripts/mic001_probe.sh 90
```

Speak continuously in both 90-second captures.

The script records:

1. `01-app-style-pulsesrc.wav` — the same explicit Pulse timing/clock
   properties used by Lite;
2. `02-default-pulsesrc.wav` — Pulse source defaults.

Listen to both WAV files completely.

Interpretation:

- app-style broken / default clean:
  explicit Lite `pulsesrc` timing/clock properties are the primary suspect;
- both broken:
  Pulse/PipeWire/source path is failing before Lite's A/V pipeline;
- both clean but Lite MP4 broken:
  the screen+audio pipeline clock relationship becomes the primary suspect.

No fix should be selected before this split is known.
