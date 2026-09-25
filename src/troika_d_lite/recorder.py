import os
from pathlib import Path
from typing import Callable, Optional

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst

from .pipeline import (
    REQUIRED_AUDIO_GST_ELEMENTS,
    REQUIRED_DUAL_AUDIO_GST_ELEMENTS,
    REQUIRED_VIDEO_GST_ELEMENTS,
    build_video_pipeline,
)
from .portal import PortalClient


FINALIZE_TIMEOUT_SECONDS = 12
AUDIO_SOURCE_NAMES = ("mic_src", "system_audio_src")
MIC_GAP_WARN_NS = 100_000_000
SCREEN_GAP_WARN_NS = 1_000_000_000


def is_wayland_session() -> bool:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    return session_type == "wayland" or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )


class Recorder:
    def __init__(
        self,
        status_cb: Callable[[str], None],
        state_cb: Callable[[bool], None],
    ) -> None:
        Gst.init(None)
        self.status_cb = status_cb
        self.state_cb = state_cb

        self.pipeline: Optional[Gst.Element] = None
        self.bus: Optional[Gst.Bus] = None
        self.bus_handler_id = 0

        self.portal: Optional[PortalClient] = None
        self.portal_session: Optional[str] = None
        self.pipewire_fd: Optional[int] = None
        self.portal_closed_subscription = 0

        self.stop_timeout_id = 0
        self.starting = False
        self.stopping = False
        self.active_fps: Optional[int] = None
        self.active_microphone = False
        self.active_system_audio = False

        self.mic_probe_pad: Optional[Gst.Pad] = None
        self.mic_probe_id = 0
        self.mic_buffer_count = 0
        self.mic_gap_count = 0
        self.mic_discont_count = 0
        self.mic_invalid_pts_count = 0
        self.mic_max_gap_ns = 0
        self.mic_last_end_ns: Optional[int] = None

        self.screen_probe_pad: Optional[Gst.Pad] = None
        self.screen_probe_id = 0
        self.screen_buffer_count = 0
        self.screen_gap_count = 0
        self.screen_max_gap_ns = 0
        self.screen_last_pts_ns: Optional[int] = None

        self.audio_runtime_logged = False

    @property
    def active(self) -> bool:
        return self.pipeline is not None

    @property
    def busy(self) -> bool:
        return (
            self.starting
            or self.pipeline is not None
            or self.portal_session is not None
        )

    def _require_runtime(
        self,
        include_audio: bool,
        include_dual_audio: bool,
    ) -> None:
        if not is_wayland_session():
            raise RuntimeError(
                "Troika D Lite currently supports Ubuntu/Wayland only"
            )

        required = list(REQUIRED_VIDEO_GST_ELEMENTS)
        if include_audio:
            required.extend(REQUIRED_AUDIO_GST_ELEMENTS)
        if include_dual_audio:
            required.extend(REQUIRED_DUAL_AUDIO_GST_ELEMENTS)

        missing = [
            name
            for name in required
            if Gst.ElementFactory.find(name) is None
        ]
        if missing:
            raise RuntimeError(
                "Missing required GStreamer elements: "
                + ", ".join(missing)
            )

    def start(
        self,
        fps: int,
        output_path: Path,
        microphone_device: Optional[str] = None,
        system_audio_device: Optional[str] = None,
    ) -> None:
        if self.busy:
            raise RuntimeError("Recorder is already busy")
        if fps not in (15, 30):
            raise ValueError("FPS must be 15 or 30")

        include_microphone = microphone_device is not None
        include_system_audio = system_audio_device is not None
        include_audio = include_microphone or include_system_audio
        include_dual_audio = include_microphone and include_system_audio

        self._require_runtime(include_audio, include_dual_audio)
        self.starting = True
        self.stopping = False

        try:
            self.status_cb("Select the monitor in the system dialog…")
            self.portal = PortalClient()
            capture = self.portal.create_screencast()
            self.portal_session = capture.session_handle
            self.pipewire_fd = capture.stream.fd
            self.portal_closed_subscription = (
                self.portal.watch_session_closed(
                    capture.session_handle,
                    self._on_portal_closed,
                )
            )

            plan = build_video_pipeline(
                capture.stream,
                fps,
                output_path,
                microphone_device=microphone_device,
                system_audio_device=system_audio_device,
            )
            pipeline = Gst.parse_launch(plan.description)
            self.pipeline = pipeline
            self.active_fps = fps
            self.active_microphone = include_microphone
            self.active_system_audio = include_system_audio
            self._reset_av_diagnostics()
            self._install_mic_diagnostics()
            self._install_screen_diagnostics()

            self.bus = pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus_handler_id = self.bus.connect(
                "message",
                self._on_message,
            )

            result = pipeline.set_state(Gst.State.PLAYING)
            if result == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError(
                    "GStreamer failed to start the recording pipeline"
                )

            self.state_cb(True)
            audio_label = ""
            if include_dual_audio:
                audio_label = " — microphone + system audio"
            elif include_microphone:
                audio_label = " — microphone"
            elif include_system_audio:
                audio_label = " — system audio"
            self.status_cb(
                f"Recording — {fps} FPS — {plan.encoder}{audio_label}"
            )
        except Exception:
            self._force_null_and_cleanup()
            raise
        finally:
            self.starting = False

    def _reset_av_diagnostics(self) -> None:
        self.mic_buffer_count = 0
        self.mic_gap_count = 0
        self.mic_discont_count = 0
        self.mic_invalid_pts_count = 0
        self.mic_max_gap_ns = 0
        self.mic_last_end_ns = None
        self.screen_buffer_count = 0
        self.screen_gap_count = 0
        self.screen_max_gap_ns = 0
        self.screen_last_pts_ns = None
        self.audio_runtime_logged = False

    def _install_mic_diagnostics(self) -> None:
        pipeline = self.pipeline
        if pipeline is None or not self.active_microphone:
            return

        source = pipeline.get_by_name("mic_src")
        if source is None:
            return
        pad = source.get_static_pad("src")
        if pad is None:
            return

        self.mic_probe_pad = pad
        self.mic_probe_id = pad.add_probe(
            Gst.PadProbeType.BUFFER,
            self._on_mic_buffer,
        )

    def _install_screen_diagnostics(self) -> None:
        pipeline = self.pipeline
        if pipeline is None or not self.active_microphone:
            return

        source = pipeline.get_by_name("screen_src")
        if source is None:
            return
        pad = source.get_static_pad("src")
        if pad is None:
            return

        self.screen_probe_pad = pad
        self.screen_probe_id = pad.add_probe(
            Gst.PadProbeType.BUFFER,
            self._on_screen_buffer,
        )

    def _remove_screen_diagnostics(self) -> None:
        if self.screen_probe_pad is not None and self.screen_probe_id:
            try:
                self.screen_probe_pad.remove_probe(self.screen_probe_id)
            except Exception:
                pass
        self.screen_probe_pad = None
        self.screen_probe_id = 0

    def _observe_screen_timing(self, pts_ns: Optional[int]) -> None:
        self.screen_buffer_count += 1
        if pts_ns is None:
            return

        if self.screen_last_pts_ns is not None:
            delta = pts_ns - self.screen_last_pts_ns
            if delta >= SCREEN_GAP_WARN_NS:
                self.screen_gap_count += 1
                self.screen_max_gap_ns = max(
                    self.screen_max_gap_ns,
                    delta,
                )
                print(
                    "SCREEN GAP: "
                    f"buffer={self.screen_buffer_count} "
                    f"gap-ms={delta / 1_000_000:.3f} "
                    f"pts-ns={pts_ns}",
                    flush=True,
                )

        self.screen_last_pts_ns = pts_ns

    def _on_screen_buffer(self, _pad, info):
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK

        pts_ns = None
        if buffer.pts != Gst.CLOCK_TIME_NONE:
            pts_ns = int(buffer.pts)
        self._observe_screen_timing(pts_ns)
        return Gst.PadProbeReturn.OK

    def _remove_mic_diagnostics(self) -> None:
        if self.mic_probe_pad is not None and self.mic_probe_id:
            try:
                self.mic_probe_pad.remove_probe(self.mic_probe_id)
            except Exception:
                pass
        self.mic_probe_pad = None
        self.mic_probe_id = 0

    def _observe_mic_timing(
        self,
        pts_ns: Optional[int],
        duration_ns: Optional[int],
        discont: bool = False,
    ) -> None:
        self.mic_buffer_count += 1
        if discont:
            self.mic_discont_count += 1
            print(
                "MIC DISCONT: "
                f"buffer={self.mic_buffer_count} "
                f"pts-ns={pts_ns}",
                flush=True,
            )

        if pts_ns is None:
            self.mic_invalid_pts_count += 1
            return

        if self.mic_last_end_ns is not None:
            delta = pts_ns - self.mic_last_end_ns
            if delta >= MIC_GAP_WARN_NS:
                self.mic_gap_count += 1
                self.mic_max_gap_ns = max(
                    self.mic_max_gap_ns,
                    delta,
                )
                print(
                    "MIC GAP: "
                    f"buffer={self.mic_buffer_count} "
                    f"gap-ms={delta / 1_000_000:.3f} "
                    f"pts-ns={pts_ns}",
                    flush=True,
                )
            elif delta <= -MIC_GAP_WARN_NS:
                print(
                    "MIC TIMESTAMP BACKWARD: "
                    f"buffer={self.mic_buffer_count} "
                    f"delta-ms={delta / 1_000_000:.3f} "
                    f"pts-ns={pts_ns}",
                    flush=True,
                )

        if duration_ns is not None and duration_ns >= 0:
            self.mic_last_end_ns = pts_ns + duration_ns
        else:
            self.mic_last_end_ns = pts_ns

    def _on_mic_buffer(self, _pad, info):
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK

        pts_ns = None
        if buffer.pts != Gst.CLOCK_TIME_NONE:
            pts_ns = int(buffer.pts)

        duration_ns = None
        if buffer.duration != Gst.CLOCK_TIME_NONE:
            duration_ns = int(buffer.duration)

        discont = bool(
            buffer.has_flags(Gst.BufferFlags.DISCONT)
        )
        self._observe_mic_timing(
            pts_ns,
            duration_ns,
            discont=discont,
        )
        return Gst.PadProbeReturn.OK

    @staticmethod
    def _property_text(value) -> str:
        return str(getattr(value, "value_nick", value))

    def _log_audio_runtime(self) -> None:
        if self.audio_runtime_logged:
            return
        pipeline = self.pipeline
        if pipeline is None:
            return

        clock = pipeline.get_clock()
        clock_name = "none"
        if clock is not None:
            try:
                clock_name = clock.get_name()
            except Exception:
                clock_name = type(clock).__name__
        print(f"Pipeline clock: {clock_name}", flush=True)

        source = pipeline.get_by_name("mic_src")
        if source is not None:
            props = {}
            for name in (
                "device",
                "buffer-time",
                "actual-buffer-time",
                "latency-time",
                "actual-latency-time",
                "provide-clock",
                "slave-method",
            ):
                try:
                    props[name] = self._property_text(
                        source.get_property(name)
                    )
                except Exception:
                    props[name] = "unavailable"
            print(
                "Mic source config: "
                + " ".join(
                    f"{name}={value}"
                    for name, value in props.items()
                ),
                flush=True,
            )

        self.audio_runtime_logged = True

    def _log_mic_timing(self, reason: str) -> None:
        if not self.active_microphone:
            return
        print(
            "Mic timing stats "
            f"[{reason}] "
            f"buffers={self.mic_buffer_count} "
            f"gaps={self.mic_gap_count} "
            f"max-gap-ms={self.mic_max_gap_ns / 1_000_000:.3f} "
            f"discont={self.mic_discont_count} "
            f"invalid-pts={self.mic_invalid_pts_count}",
            flush=True,
        )
    def _log_screen_timing(self, reason: str) -> None:
        if not self.active_microphone:
            return
        print(
            "Screen source timing stats "
            f"[{reason}] "
            f"buffers={self.screen_buffer_count} "
            f"gaps={self.screen_gap_count} "
            f"max-gap-ms={self.screen_max_gap_ns / 1_000_000:.3f}",
            flush=True,
        )

    def _log_queue_levels(self, reason: str) -> None:
        pipeline = self.pipeline
        if pipeline is None:
            return

        parts = []
        for name in (
            "mic_capture_q",
            "audio_mux_q",
            "video_capture_q",
            "video_mux_q",
        ):
            queue = pipeline.get_by_name(name)
            if queue is None:
                continue
            try:
                level_time = int(
                    queue.get_property("current-level-time")
                )
                level_buffers = int(
                    queue.get_property("current-level-buffers")
                )
                max_time = int(queue.get_property("max-size-time"))
            except Exception:
                continue
            parts.append(
                f"{name}:"
                f"time-ms={level_time / 1_000_000:.3f},"
                f"buffers={level_buffers},"
                f"max-ms={max_time / 1_000_000:.3f}"
            )

        print(
            f"Queue levels [{reason}] "
            + (" ".join(parts) if parts else "unavailable"),
            flush=True,
        )

    def stop(self) -> None:
        pipeline = self.pipeline
        if pipeline is None or self.stopping:
            return

        self.stopping = True
        self.status_cb("Finalizing recording…")

        source_results = {}
        video_stop_name = (
            "video_hold"
            if pipeline.get_by_name("video_hold") is not None
            else "screen_src"
        )
        stop_source_names = (
            video_stop_name,
            *AUDIO_SOURCE_NAMES,
        )
        for name in stop_source_names:
            source = pipeline.get_by_name(name)
            if source is None:
                continue
            pad = source.get_static_pad("src")
            if pad is None:
                source_results[name] = False
                continue
            try:
                source_results[name] = bool(
                    pad.push_event(Gst.Event.new_eos())
                )
            except Exception:
                source_results[name] = False

        accepted = bool(source_results) and all(
            source_results.values()
        )
        pipeline_fallback = False
        if not accepted:
            pipeline_fallback = True
            try:
                accepted = bool(
                    pipeline.send_event(Gst.Event.new_eos())
                )
            except Exception:
                accepted = False

        summary = ",".join(
            f"{name}:{int(ok)}"
            for name, ok in source_results.items()
        ) or "none"
        print(
            "EOS request: "
            f"source-pads=[{summary}] "
            f"pipeline-fallback={int(pipeline_fallback)} "
            f"accepted={int(accepted)}",
            flush=True,
        )

        if not accepted:
            self.status_cb(
                "Clean EOS was not accepted; closing with robust MP4 state."
            )
            self._log_video_timing("eos-rejected")
            self._log_mic_timing("eos-rejected")
            self._log_screen_timing("eos-rejected")
            self._force_null_and_cleanup()
            return

        self.stop_timeout_id = GLib.timeout_add_seconds(
            FINALIZE_TIMEOUT_SECONDS,
            self._on_finalize_timeout,
        )

    def _log_video_timing(self, reason: str) -> None:
        pipeline = self.pipeline
        if pipeline is None:
            return
        rate = pipeline.get_by_name("video_rate")
        if rate is None:
            return
        try:
            values = {
                "in": rate.get_property("in"),
                "out": rate.get_property("out"),
                "drop": rate.get_property("drop"),
                "duplicate": rate.get_property("duplicate"),
            }
        except Exception:
            return

        print(
            "Video timing stats "
            f"[{reason}] fps={self.active_fps} "
            f"mic={int(self.active_microphone)} "
            f"system={int(self.active_system_audio)} "
            f"in={values['in']} out={values['out']} "
            f"drop={values['drop']} "
            f"duplicate={values['duplicate']}",
            flush=True,
        )

    def _on_finalize_timeout(self) -> bool:
        self.stop_timeout_id = 0
        if self.pipeline is None:
            return False

        self.status_cb(
            "Finalization timeout — closing with robust MP4 state."
        )
        self._log_video_timing("finalize-timeout")
        self._log_mic_timing("finalize-timeout")
        self._log_screen_timing("finalize-timeout")
        self._force_null_and_cleanup()
        return False

    def _on_portal_closed(self) -> None:
        GLib.idle_add(self._handle_external_portal_close)

    def _handle_external_portal_close(self) -> bool:
        if self.pipeline is None:
            return False

        self.stopping = True
        self.status_cb(
            "Screen sharing was stopped by the system — closing safely."
        )
        self._log_video_timing("external-portal-stop")
        self._log_mic_timing("external-portal-stop")
        self._log_screen_timing("external-portal-stop")
        self._force_null_and_cleanup(portal_already_closed=True)
        return False

    def _on_message(self, _bus, message) -> None:
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self._log_video_timing("error")
            self._log_mic_timing("error")
            self._log_screen_timing("error")
            if debug:
                print(debug, flush=True)
            self.status_cb(f"Recording error: {err.message}")
            self._force_null_and_cleanup()

        elif message.type == Gst.MessageType.EOS:
            self._log_video_timing("eos")
            self._log_mic_timing("eos")
            self._log_screen_timing("eos")
            pipeline = self.pipeline
            if pipeline is not None:
                pipeline.set_state(Gst.State.NULL)
            self.status_cb("Saved")
            self._cleanup()

        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                _old, new, _pending = message.parse_state_changed()
                if new == Gst.State.PLAYING:
                    self._log_audio_runtime()

        elif message.type == Gst.MessageType.CLOCK_LOST:
            source_name = (
                message.src.get_name()
                if message.src is not None
                else "unknown"
            )
            print(
                f"GStreamer CLOCK_LOST source={source_name}",
                flush=True,
            )

        elif message.type == Gst.MessageType.QOS:
            source_name = (
                message.src.get_name()
                if message.src is not None
                else "unknown"
            )
            print(
                f"GStreamer QOS source={source_name}",
                flush=True,
            )

        elif message.type == Gst.MessageType.LATENCY:
            source_name = (
                message.src.get_name()
                if message.src is not None
                else "unknown"
            )
            print(
                f"GStreamer LATENCY source={source_name}",
                flush=True,
            )

        elif message.type == Gst.MessageType.WARNING:
            warning, debug = message.parse_warning()
            source_name = (
                message.src.get_name()
                if message.src is not None
                else "unknown"
            )
            print(
                "GStreamer WARNING "
                f"source={source_name}: {warning.message}",
                flush=True,
            )
            if (
                source_name == "mic_src"
                and "Can't record audio fast enough" in warning.message
            ):
                self._log_queue_levels("mic-backpressure")
            if debug:
                print(debug, flush=True)

    def _force_null_and_cleanup(
        self,
        portal_already_closed: bool = False,
    ) -> None:
        pipeline = self.pipeline
        if pipeline is not None:
            pipeline.set_state(Gst.State.NULL)
        self._cleanup(portal_already_closed=portal_already_closed)

    def _cleanup(
        self,
        portal_already_closed: bool = False,
    ) -> None:
        was_active = self.pipeline is not None

        if self.stop_timeout_id:
            GLib.source_remove(self.stop_timeout_id)
            self.stop_timeout_id = 0

        self._remove_mic_diagnostics()
        self._remove_screen_diagnostics()

        if self.bus is not None:
            if self.bus_handler_id:
                try:
                    self.bus.disconnect(self.bus_handler_id)
                except Exception:
                    pass
                self.bus_handler_id = 0
            try:
                self.bus.remove_signal_watch()
            except Exception:
                pass
            self.bus = None

        if self.portal and self.portal_closed_subscription:
            self.portal.unwatch_session(
                self.portal_closed_subscription
            )
            self.portal_closed_subscription = 0

        self.pipeline = None

        if (
            not portal_already_closed
            and self.portal
            and self.portal_session
        ):
            self.portal.close_session(self.portal_session)

        self.portal_session = None

        if self.pipewire_fd is not None:
            try:
                os.close(self.pipewire_fd)
            except OSError:
                pass
            self.pipewire_fd = None

        self.portal = None
        self.starting = False
        self.stopping = False
        self.active_fps = None
        self.active_microphone = False
        self.active_system_audio = False

        if was_active:
            self.state_cb(False)
