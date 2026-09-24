import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import gi

# Pin GTK and GDK before importing either namespace. This prevents the
# GTK3/GDK3 vs GTK4 namespace conflict seen during Troika D field work.
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from .portal import PortalCancelled
from .recorder import Recorder


APP_ID = "io.github.scientifica007.TroikaDLite"


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
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(
            application=application,
            title="Troika D Lite",
        )
        self.set_default_size(360, 230)
        self.set_border_width(20)

        self.recorder = Recorder(
            status_cb=self._set_status,
            state_cb=self._on_recording_state,
        )

        self._timer_id = 0
        self._started_us = 0
        self._close_after_stop = False

        self.connect("delete-event", self._on_delete_event)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
        )
        self.add(root)

        title = Gtk.Label()
        title.set_markup("<b>Troika D Lite</b>")
        root.pack_start(title, False, False, 0)

        self.stack = Gtk.Stack()
        root.pack_start(self.stack, True, True, 0)

        idle = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        self.stack.add_named(idle, "idle")

        fps_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )
        fps_box.pack_start(
            Gtk.Label(label="Frame rate:"),
            False,
            False,
            0,
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

        start = Gtk.Button(label="Start Recording")
        start.connect("clicked", self._on_start)
        idle.pack_start(start, False, False, 0)

        recording = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
        )
        self.stack.add_named(recording, "recording")

        self.timer_label = Gtk.Label(label="Recording 00:00:00")
        recording.pack_start(self.timer_label, False, False, 0)

        stop = Gtk.Button(label="Stop")
        stop.connect("clicked", self._on_stop)
        recording.pack_start(stop, False, False, 0)

        self.status = Gtk.Label(label="L1 video-only milestone")
        self.status.set_line_wrap(True)
        root.pack_end(self.status, False, False, 0)

        self.stack.set_visible_child_name("idle")
        self.show_all()

    def _selected_fps(self) -> int:
        return 15 if self.fps_15.get_active() else 30

    def _set_status(self, text: str) -> None:
        self.status.set_text(text)

    def _on_start(self, _button) -> None:
        output_path = collision_safe_output_path(
            Path.home() / "Videos"
        )
        try:
            self.recorder.start(
                self._selected_fps(),
                output_path,
            )
        except PortalCancelled:
            self._set_status("Screen selection cancelled")
        except Exception as exc:
            self._show_error(str(exc))

    def _on_stop(self, _button) -> None:
        self.recorder.stop()

    def _on_recording_state(self, active: bool) -> None:
        if active:
            self.stack.set_visible_child_name("recording")
            self._started_us = GLib.get_monotonic_time()
            self._update_timer()
            if not self._timer_id:
                self._timer_id = GLib.timeout_add_seconds(
                    1,
                    self._update_timer,
                )
            return

        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0
        self.stack.set_visible_child_name("idle")

        if self._close_after_stop:
            self._close_after_stop = False
            GLib.idle_add(self.destroy)

    def _update_timer(self) -> bool:
        if not self.recorder.active:
            return False

        elapsed = max(
            0,
            (GLib.get_monotonic_time() - self._started_us)
            // 1_000_000,
        )
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_label.set_text(
            f"Recording {hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        return True

    def _on_delete_event(self, _widget, _event) -> bool:
        if not self.recorder.active:
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
            text="Troika D Lite",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main() -> int:
    app = Gtk.Application(application_id=APP_ID)

    def on_activate(application: Gtk.Application) -> None:
        window = RecorderWindow(application)
        window.present()

    app.connect("activate", on_activate)
    return app.run(sys.argv)
