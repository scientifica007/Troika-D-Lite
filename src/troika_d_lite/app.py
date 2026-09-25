import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import gi

# Pin GTK and GDK before importing either namespace. This prevents the
# GTK3/GDK3 vs GTK4 namespace conflict seen during Troika D field work.
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from .audio import (
    default_microphone_source,
    default_system_audio_source,
    list_microphones,
    list_system_audio_sources,
)
from .portal import PortalCancelled
from .recorder import Recorder


APP_ID = "io.github.scientifica007.TroikaDLite"
APP_NAME = "Troika D Lite"

_CSS = b"""
#section-title {
  font-weight: 600;
}
#recording-state {
  font-weight: 600;
}
"""


def default_output_directory() -> Path:
    return Path.home() / "Videos"


def audio_mode_label(
    microphone_enabled: bool,
    system_audio_enabled: bool,
) -> str:
    if microphone_enabled and system_audio_enabled:
        return "Microphone + system audio"
    if microphone_enabled:
        return "Microphone"
    if system_audio_enabled:
        return "System audio"
    return "Video only"


def display_output_path(
    path: Path,
    home: Optional[Path] = None,
) -> str:
    home_dir = home or Path.home()
    try:
        return "~/" + str(path.relative_to(home_dir))
    except ValueError:
        return str(path)


def collision_safe_output_path(
    directory: Path,
    now: Optional[datetime] = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.now()
    stamp = moment.strftime("%Y-%m-%d_%H-%M-%S")
    stem = f"TroikaD-Lite_{stamp}"

    candidate = directory / f"{stem}.mp4"
    if not candidate.exists():
        return candidate

    for index in range(1, 10_000):
        candidate = directory / f"{stem}_{index:02d}.mp4"
        if not candidate.exists():
            return candidate

    raise RuntimeError("Could not allocate a collision-safe output name")


class RecorderWindow(Gtk.ApplicationWindow):
    DEVICE_POLL_SECONDS = 2

    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(
            application=application,
            title=APP_NAME,
        )
        self.set_default_size(430, 400)
        self.set_size_request(390, 350)
        self.set_border_width(20)

        self._install_css()

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = APP_NAME
        header.props.subtitle = "Screen & audio recorder"
        self.set_titlebar(header)

        self.recorder = Recorder(
            status_cb=self._set_status,
            state_cb=self._on_recording_state,
        )

        self.microphones = list_microphones()
        self.system_audio_sources = list_system_audio_sources()
        self._audio_signature = self._make_audio_signature()

        self._device_poll_id = 0
        self._close_after_stop = False
        self._starting = False
        self._last_output_path: Optional[Path] = None

        self.connect("delete-event", self._on_delete_event)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        self.add(root)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        root.pack_start(self.stack, True, True, 0)

        idle = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        self.stack.add_named(idle, "idle")
        self._build_idle_ui(idle)

        recording = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        self.stack.add_named(recording, "recording")
        self._build_recording_ui(recording)

        root.pack_end(Gtk.Separator(), False, False, 0)

        self.status = Gtk.Label(
            label=f"Ready — recordings are saved to "
            f"{display_output_path(default_output_directory())}"
        )
        self.status.set_line_wrap(True)
        self.status.set_xalign(0.0)
        self.status.get_style_context().add_class("dim-label")
        root.pack_end(self.status, False, False, 0)

        self.stack.set_visible_child_name("idle")
        self._sync_audio_ui()
        self._device_poll_id = GLib.timeout_add_seconds(
            self.DEVICE_POLL_SECONDS,
            self._poll_audio_devices,
        )
        self.show_all()

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _section_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_xalign(0.0)
        label.set_name("section-title")
        return label

    def _build_idle_ui(self, idle: Gtk.Box) -> None:
        idle.pack_start(self._section_label("Audio"), False, False, 0)

        self.mic_check = Gtk.CheckButton(label="Record microphone")
        self.mic_check.set_active(False)
        self.mic_check.connect("toggled", self._sync_audio_ui)
        idle.pack_start(self.mic_check, False, False, 0)

        self.mic_combo = Gtk.ComboBoxText()
        self.mic_combo.set_margin_start(24)
        self._populate_microphones()
        idle.pack_start(self.mic_combo, False, False, 0)

        self.system_check = Gtk.CheckButton(label="Record system audio")
        self.system_check.set_active(False)
        self.system_check.connect("toggled", self._sync_audio_ui)
        idle.pack_start(self.system_check, False, False, 0)

        idle.pack_start(Gtk.Separator(), False, False, 2)
        idle.pack_start(self._section_label("Frame rate"), False, False, 0)

        fps_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=18,
        )
        self.fps_15 = Gtk.RadioButton.new_with_label_from_widget(
            None,
            "15 FPS",
        )
        self.fps_30 = Gtk.RadioButton.new_with_label_from_widget(
            self.fps_15,
            "30 FPS",
        )
        self.fps_30.set_active(True)
        fps_box.pack_start(self.fps_15, False, False, 0)
        fps_box.pack_start(self.fps_30, False, False, 0)
        idle.pack_start(fps_box, False, False, 0)

        idle.pack_start(Gtk.Separator(), False, False, 2)

        self.start_button = Gtk.Button(label="Start Recording")
        self.start_button.set_can_default(True)
        self.start_button.get_style_context().add_class(
            "suggested-action"
        )
        self.start_button.connect("clicked", self._on_start)
        idle.pack_start(self.start_button, False, False, 0)

    def _build_recording_ui(self, recording: Gtk.Box) -> None:
        state = Gtk.Label(label="Recording")
        state.set_name("recording-state")
        recording.pack_start(state, False, False, 8)

        self.recording_summary = Gtk.Label(label="")
        self.recording_summary.get_style_context().add_class("dim-label")
        recording.pack_start(
            self.recording_summary,
            False,
            False,
            0,
        )

        stop = Gtk.Button(label="Stop Recording")
        stop.get_style_context().add_class("destructive-action")
        stop.connect("clicked", self._on_stop)
        recording.pack_start(stop, False, False, 10)

    def _selected_fps(self) -> int:
        return 15 if self.fps_15.get_active() else 30

    def _set_status(self, text: str) -> None:
        if text == "Saved" and self._last_output_path is not None:
            text = (
                "Saved to "
                + display_output_path(self._last_output_path)
            )
        self.status.set_text(text)

    def _make_audio_signature(self):
        microphones = tuple(
            (source.name, source.description)
            for source in self.microphones
        )
        system = tuple(
            (source.name, source.description)
            for source in self.system_audio_sources
        )
        return microphones, system

    def _populate_microphones(
        self,
        preferred_id: Optional[str] = None,
    ) -> None:
        self.mic_combo.remove_all()
        ids = []
        for source in self.microphones:
            self.mic_combo.append(source.name, source.description)
            ids.append(source.name)

        default_id = default_microphone_source(self.microphones)
        if preferred_id and preferred_id in ids:
            self.mic_combo.set_active_id(preferred_id)
        elif default_id and default_id in ids:
            self.mic_combo.set_active_id(default_id)
        elif ids:
            self.mic_combo.set_active(0)

    def _sync_audio_ui(self, *_args) -> None:
        mic_available = bool(self.microphones)
        system_available = bool(self.system_audio_sources)

        if self._starting:
            self.mic_check.set_sensitive(False)
            self.system_check.set_sensitive(False)
            self.mic_combo.set_sensitive(False)
            return

        self.mic_check.set_sensitive(mic_available)
        if not mic_available and self.mic_check.get_active():
            self.mic_check.set_active(False)

        self.system_check.set_sensitive(system_available)
        if not system_available and self.system_check.get_active():
            self.system_check.set_active(False)

        self.mic_combo.set_sensitive(
            mic_available and self.mic_check.get_active()
        )

    def _set_start_pending(self, pending: bool) -> None:
        self._starting = pending
        self.start_button.set_sensitive(not pending)
        self.fps_15.set_sensitive(not pending)
        self.fps_30.set_sensitive(not pending)
        self._sync_audio_ui()

    def _refresh_audio_devices(self) -> bool:
        if self._starting or self.recorder.busy:
            return False

        new_microphones = list_microphones()
        new_system_audio = list_system_audio_sources()
        new_signature = (
            tuple(
                (source.name, source.description)
                for source in new_microphones
            ),
            tuple(
                (source.name, source.description)
                for source in new_system_audio
            ),
        )
        if new_signature == self._audio_signature:
            return False

        preferred = self.mic_combo.get_active_id()
        self.microphones = new_microphones
        self.system_audio_sources = new_system_audio
        self._audio_signature = new_signature
        self._populate_microphones(preferred)
        self._sync_audio_ui()
        self._set_status("Audio devices updated")
        return True

    def _poll_audio_devices(self) -> bool:
        if not self._starting and not self.recorder.busy:
            self._refresh_audio_devices()
        return True

    def _selected_microphone(self) -> Optional[str]:
        if not self.mic_check.get_active():
            return None
        return self.mic_combo.get_active_id()

    def _selected_system_audio(self) -> Optional[str]:
        if not self.system_check.get_active():
            return None
        return default_system_audio_source(self.system_audio_sources)

    def _on_start(self, _button) -> None:
        if self._starting or self.recorder.busy:
            return

        self._refresh_audio_devices()

        microphone = self._selected_microphone()
        system_audio = self._selected_system_audio()

        if self.mic_check.get_active() and not microphone:
            self._show_error("No microphone is available")
            return
        if self.system_check.get_active() and not system_audio:
            self._show_error("No system-audio monitor is available")
            return

        output_path = collision_safe_output_path(
            default_output_directory()
        )
        self._last_output_path = output_path
        self._set_start_pending(True)
        try:
            self.recorder.start(
                self._selected_fps(),
                output_path,
                microphone_device=microphone,
                system_audio_device=system_audio,
            )
        except PortalCancelled:
            self._set_status("Screen selection cancelled")
        except Exception as exc:
            self._show_error(str(exc))
        finally:
            self._set_start_pending(False)

    def _on_stop(self, _button) -> None:
        self.recorder.stop()

    def _on_recording_state(self, active: bool) -> None:
        if active:
            self.recording_summary.set_text(
                f"{self._selected_fps()} FPS · "
                + audio_mode_label(
                    self.mic_check.get_active(),
                    self.system_check.get_active(),
                )
            )
            self.stack.set_visible_child_name("recording")
            return

        self.stack.set_visible_child_name("idle")
        self._refresh_audio_devices()

        if self._close_after_stop:
            self._close_after_stop = False
            self._remove_device_poll()
            GLib.idle_add(self.destroy)

    def _remove_device_poll(self) -> None:
        if self._device_poll_id:
            GLib.source_remove(self._device_poll_id)
            self._device_poll_id = 0

    def _on_delete_event(self, _widget, _event) -> bool:
        if self._starting or self.recorder.starting:
            self._set_status(
                "Cancel the screen-selection dialog before closing."
            )
            return True

        if not self.recorder.active:
            self._remove_device_poll()
            return False

        self._close_after_stop = True
        self.recorder.stop()
        return True

    def _show_error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=APP_NAME,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main() -> int:
    Gtk.Window.set_default_icon_name(APP_ID)
    app = Gtk.Application(application_id=APP_ID)

    def on_activate(application: Gtk.Application) -> None:
        windows = application.get_windows()
        if windows:
            windows[0].present()
            return
        window = RecorderWindow(application)
        window.present()

    app.connect("activate", on_activate)
    return app.run(sys.argv)
