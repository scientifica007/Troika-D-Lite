# L3 Field Test — 2026-09-25

## Tested build

Repository: `scientifica007/Troika-D-Lite`

Branch: `milestone/l3-system-audio`

Runtime commit tested:

```
ea8da18556bd6b787c74a0ee52ee7cefe36eb01e
```

Target environment: Ubuntu 24.04 / Wayland.

## Human acceptance result

The complete L3 human field gate was reported PASS on 2026-09-25.

Validated:

1. video-only recording remained good;
2. microphone recording remained good;
3. system audio at 15 FPS was audible, playable, and synchronized;
4. system audio at 30 FPS was audible, playable, and synchronized;
5. normal Stop with system audio finalized playable MP4 output;
6. close-while-recording with system audio finalized safely;
7. system-side Portal/GNOME Stop returned safely to idle;
8. the default output monitor was selected correctly;
9. idle device/default-output refresh behavior worked without restarting the app;
10. no unacceptable video regression, audio drift, broken audio, or system-audio finalization failure was observed.

## Representative system-audio evidence

```text
EOS request: source-pads=[screen_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=1 in=706 out=295 drop=412 duplicate=1

EOS request: source-pads=[screen_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=0 system=1 in=424 out=641 drop=26 duplicate=243

Video timing stats [external-portal-stop] fps=30 mic=0 system=1 in=263 out=321 drop=13 duplicate=72

EOS request: source-pads=[screen_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=1 in=648 out=374 drop=292 duplicate=18
```

The accepted L2 microphone path also remained healthy:

```text
EOS request: source-pads=[screen_src:1,mic_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=1 system=0 in=284 out=436 drop=12 duplicate=164
```

## Isolated finalization recovery event

One video-only 15 FPS run produced:

```text
EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [finalize-timeout] fps=15 mic=0 system=0 in=185 out=376 drop=100 duplicate=292
```

The user reported the recording itself as successful. This occurred outside the new system-audio path and exercised the existing bounded 12-second recovery behavior.

Because reliability is a product requirement, this event was not ignored. A focused repeatability check was required before accepting L3.

## Focused repeatability check

Five consecutive normal video-only 15 FPS runs were repeated with microphone OFF and system audio OFF.

All five ended through normal bus EOS and none reproduced `finalize-timeout`:

```text
EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=0 in=902 out=627 drop=376 duplicate=101

EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=0 in=753 out=450 drop=314 duplicate=11

EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=0 in=957 out=565 drop=398 duplicate=6

EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=0 in=898 out=544 drop=393 duplicate=39

EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=0 in=916 out=538 drop=405 duplicate=27
```

An additional external Portal Stop and a further normal 15 FPS run also completed without a finalization timeout:

```text
Video timing stats [external-portal-stop] fps=15 mic=0 system=0 in=363 out=195 drop=169 duplicate=2

EOS request: source-pads=[screen_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=15 mic=0 system=0 in=301 out=149 drop=162 duplicate=10
```

## Interpretation

The earlier timeout is classified as an isolated bounded-recovery event, not a reproducible L3 regression.

It remains useful reliability evidence and should be retained for later performance/finalization analysis. If similar events recur in future milestones, they should be aggregated rather than treated as unrelated incidents.

The videorate `drop` and `duplicate` counters remain diagnostic baseline data only and are not standalone quality verdicts.

## L3 decision

**L3 HUMAN FIELD GATE: PASS**

L3 is accepted as the stable system-audio-capable baseline.

This validates:
- video-only;
- microphone-only;
- system-audio-only.

Simultaneous microphone + system-audio mixing remains unvalidated and is reserved for L4.
