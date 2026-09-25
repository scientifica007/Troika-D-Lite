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
SOURCE_NAMES = ("screen_src", "mic_src", "system_audio_src")


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

    def stop(self) -> None:
        pipeline = self.pipeline
        if pipeline is None or self.stopping:
            return

        self.stopping = True
        self.status_cb("Finalizing recording…")

        source_results = {}
        for name in SOURCE_NAMES:
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
        self._force_null_and_cleanup(portal_already_closed=True)
        return False

    def _on_message(self, _bus, message) -> None:
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self._log_video_timing("error")
            if debug:
                print(debug, flush=True)
            self.status_cb(f"Recording error: {err.message}")
            self._force_null_and_cleanup()

        elif message.type == Gst.MessageType.EOS:
            self._log_video_timing("eos")
            pipeline = self.pipeline
            if pipeline is not None:
                pipeline.set_state(Gst.State.NULL)
            self.status_cb("Saved")
            self._cleanup()

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
