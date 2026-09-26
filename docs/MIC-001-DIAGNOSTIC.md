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


## Field isolation result — 2026-09-25

The first diagnostic run reproduced the MP4 microphone dropout.

The in-app instrumentation showed:

- selected pipeline clock: `pipewireclock0`;
- mic source actual buffer time: 500 ms;
- mic source actual latency: 20 ms;
- `provide-clock=false`;
- `slave-method=resample`;
- repeated `Can't record audio fast enough` warnings;
- source-boundary timestamp gaps of 25.160 s, 620 ms, 7.000 s, and 640 ms;
- final maximum microphone gap: 25.160 s.

Both standalone WAV captures were clean:

1. Lite-style explicit Pulse timing/clock settings;
2. default Pulse settings.

The Lite-style standalone pipeline selected `GstSystemClock`; the default
standalone pipeline selected `GstPulseSrcClock`.

The original Troika D application also reproduces the microphone-dropout
symptom, consistent with the shared screen/audio clock architecture.

### Root-cause hypothesis

The evidence rules out a physical microphone-specific failure and makes
the explicit Lite Pulse buffer/latency properties insufficient to explain
the defect.

The failing condition is the combined screen+microphone pipeline selecting
the PipeWire video clock while `pulsesrc` is forced to slave/resample to
that clock.

## Fix candidate

When microphone capture is enabled, force the top-level GStreamer pipeline
to use `GstSystemClock` before PLAYING.

Scope intentionally unchanged:

- Pulse buffer time remains 500 ms;
- Pulse latency remains 20 ms;
- `slave-method=resample` remains;
- audio queues remain 3 s;
- AAC encoder remains unchanged;
- video pipeline remains unchanged;
- system-audio-only and video-only continue using automatic clock selection.

The candidate must not merge until field testing confirms:

- the runtime log reports `Pipeline clock: GstSystemClock`;
- long microphone gaps disappear;
- `Can't record audio fast enough` does not recur;
- recorded microphone audio is continuous;
- video remains acceptable;
- dual-audio remains synchronized.


## System-clock candidate result

Forcing `GstSystemClock` was tested in the combined screen+microphone
pipeline and **failed** to resolve MIC-001.

The candidate did select `GstSystemClock`, but the microphone still
reported repeated source-boundary gaps, including:

- 2.800 s;
- 15.000 s;
- 14.240 s;
- 30.680 s.

GStreamer explicitly reported that samples were dropped because downstream
was consuming audio too slowly.

The final diagnostic summary for that run was:

```text
buffers=6166 gaps=10 max-gap-ms=30680.000 discont=11 invalid-pts=0
```

Therefore clock selection alone is not the root cause and the forced-clock
candidate is removed.

A further field observation is decisive: original Troika D records
**audio-only** cleanly, but the combined screen+microphone mode exhibits
the same dropout defect as Lite.

This shifts the investigation from microphone capture/clock selection to
**A/V downstream backpressure**.

## Backpressure diagnostic

The diagnostic branch now also:

- measures timestamp gaps directly at `screen_src`;
- reports final screen-source gap statistics;
- snapshots queue levels when `mic_src` emits
  `Can't record audio fast enough`.

The queue snapshot includes:

- `mic_capture_q`;
- `audio_mux_q`;
- `video_capture_q`;
- `video_mux_q`.

If the audio queues are at/near their configured 3-second maximum while
the video side is starved or not advancing, that confirms that downstream
A/V aggregation is blocking the microphone source long enough to overflow
its live capture ringbuffer.


## Synthetic continuous-video A/V probe

To separate the generic x264/mp4mux path from the Portal/PipeWire screen
source, run:

```bash
bash scripts/mic001_av_probe.sh 90
```

This creates a continuously-producing 15 FPS `videotestsrc` plus the real
microphone, using the same x264 bitrate/preset, AAC bitrate, 3-second queues,
and robust `mp4mux` settings as Lite.

Interpretation:

- synthetic A/V also drops microphone samples:
  investigate generic encoder/mux scheduling or machine saturation;
- synthetic A/V is clean while Portal screen + mic drops:
  the failure depends on the real screen source delivery pattern and its
  interaction with downstream A/V aggregation.


## Heartbeat fix candidate

The backpressure run correlated long screen-source gaps directly with audio
queue saturation and microphone sample loss. Representative evidence:

- screen gap: 10.687 s -> microphone gap: 4.440 s;
- screen gap: 12.686 s -> microphone gap: 6.760 s;
- screen gap: 19.497 s -> microphone gap: 13.460 s;
- audio mux queue repeatedly reached approximately 2.8–3.0 s;
- video mux queue was usually empty during the same failures;
- GStreamer reported that `pulsesrc` dropped samples because downstream
  was consuming too slowly.

This is sufficient to test a targeted fix.

When any audio stream is enabled, the video branch now inserts:

```text
imagefreeze name=video_hold is-live=true allow-replace=true
```

before the fixed-framerate stage.

The element continuously emits the latest screen frame at the negotiated
15/30 FPS even when the PipeWire screen source produces no new damage frame.
When a real screen frame arrives, `allow-replace=true` makes it become the
new frame being emitted.

Video-only mode intentionally retains the old sparse path to avoid imposing
continuous encoding load where A/V mux synchronization is not required.

The fix candidate changes no audio source, buffer, latency, queue, codec,
mux, Portal, or stop/finalization setting.

Field acceptance for MIC-001 requires:

- no `Can't record audio fast enough` warning;
- no long `MIC GAP`;
- continuous microphone audio by listening;
- acceptable video motion and A/V sync;
- clean EOS;
- CPU impact measured after correctness is established.


## Heartbeat Stop regression — field result

The first heartbeat field test resolved the microphone dropout:

```text
Mic timing stats [finalize-timeout] buffers=7518 gaps=0 max-gap-ms=0.000 discont=1 invalid-pts=0
```

The user confirmed that microphone audio was continuous and clear.

Long raw PipeWire screen gaps remained, including a maximum gap of
34.184 s, but no microphone backpressure returned. This validates the
heartbeat concept for A/V continuity.

However, Stop regressed:

- EOS was pushed to `screen_src` and `mic_src`;
- microphone audio stopped immediately;
- `imagefreeze` continued emitting the held video frame;
- the mux did not reach EOS;
- the recorder closed only through the 12-second
  `finalize-timeout`.

### Stop fix candidate

When `video_hold` exists, the recorder now terminates the downstream
video heartbeat by pushing EOS on `video_hold:src` instead of
`screen_src:src`.

Active microphone/system-audio source pads still receive EOS exactly as
before.

When no `video_hold` exists (video-only recording), Stop continues to
push EOS to `screen_src:src`.

Field acceptance now requires both:

1. continuous audio with no MIC GAP/backpressure;
2. normal EOS finalization without `finalize-timeout`, with audio and
   video ending together.


## 30 FPS high-motion field result

The heartbeat + Stop fix passes the 15 FPS microphone gate, but a 30 FPS
microphone-only run developed transient A/V backlog after high-motion
YouTube playback began.

Observed during failure:

```text
mic_capture_q: 3000 ms
audio_mux_q:   2517 ms
video_mux_q:   2733 ms
```

The run produced four microphone gaps with a maximum gap of 2.440 s and
GStreamer reported dropped microphone samples because downstream was not
consuming quickly enough.

Unlike the original sparse-screen failure, `video_mux_q` was also heavily
backed up. The heartbeat remained active and Stop/EOS completed normally.

### x264 load diagnostic

To isolate whether software H.264 encoding load is the dominant remaining
30 FPS bottleneck, the diagnostic branch temporarily selects:

```text
30 FPS + any audio -> x264 speed-preset=ultrafast
15 FPS             -> x264 speed-preset=veryfast
30 FPS video-only  -> x264 speed-preset=veryfast
```

No bitrate, audio, queue, mux, heartbeat, or Stop setting changes in this
diagnostic.

If high-motion 30 FPS recording becomes stable, the next step is to test
`superfast` as a potential quality/performance compromise before choosing
a production preset.
