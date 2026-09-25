import unittest
from pathlib import Path
from unittest.mock import patch

from troika_d_lite.recorder import MIC_GAP_WARN_NS, Recorder


class _Pad:
    def __init__(self):
        self.events = 0

    def push_event(self, _event):
        self.events += 1
        return True


class _Source:
    def __init__(self):
        self.pad = _Pad()

    def get_static_pad(self, name):
        return self.pad if name == "src" else None


class _ClockPipeline:
    def __init__(self):
        self.used_clock = None

    def use_clock(self, clock):
        self.used_clock = clock


class _Pipeline:
    def __init__(self, include_mic=False, include_system=False):
        self.screen = _Source()
        self.mic = _Source() if include_mic else None
        self.system = _Source() if include_system else None
        self.fallback_events = 0

    def get_by_name(self, name):
        if name == "screen_src":
            return self.screen
        if name == "mic_src":
            return self.mic
        if name == "system_audio_src":
            return self.system
        return None

    def send_event(self, _event):
        self.fallback_events += 1
        return True


class RecorderStartGuardTests(unittest.TestCase):
    def test_start_rejects_reentry_while_portal_request_is_pending(self):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        recorder.starting = True

        with self.assertRaisesRegex(RuntimeError, "already busy"):
            recorder.start(30, Path("/tmp/a.mp4"))

    def test_busy_includes_starting_state(self):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        self.assertFalse(recorder.busy)
        recorder.starting = True
        self.assertTrue(recorder.busy)


class RecorderClockPolicyTests(unittest.TestCase):
    @patch("troika_d_lite.recorder.Gst.SystemClock.obtain")
    def test_microphone_forces_system_clock(self, obtain):
        fake_clock = object()
        obtain.return_value = fake_clock

        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _ClockPipeline()
        recorder.pipeline = pipeline
        recorder.active_microphone = True

        recorder._configure_capture_clock()

        obtain.assert_called_once_with()
        self.assertIs(pipeline.used_clock, fake_clock)
        self.assertIs(recorder.forced_system_clock, fake_clock)

    @patch("troika_d_lite.recorder.Gst.SystemClock.obtain")
    def test_without_microphone_keeps_automatic_clock(self, obtain):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _ClockPipeline()
        recorder.pipeline = pipeline
        recorder.active_microphone = False

        recorder._configure_capture_clock()

        obtain.assert_not_called()
        self.assertIsNone(pipeline.used_clock)
        self.assertIsNone(recorder.forced_system_clock)


class RecorderMicrophoneDiagnosticTests(unittest.TestCase):
    def test_continuous_buffers_do_not_count_as_gap(self):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        duration = 20_000_000
        recorder._observe_mic_timing(0, duration)
        recorder._observe_mic_timing(duration, duration)
        recorder._observe_mic_timing(duration * 2, duration)

        self.assertEqual(recorder.mic_buffer_count, 3)
        self.assertEqual(recorder.mic_gap_count, 0)
        self.assertEqual(recorder.mic_max_gap_ns, 0)

    def test_large_timestamp_gap_is_recorded(self):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        duration = 20_000_000
        recorder._observe_mic_timing(0, duration)
        recorder._observe_mic_timing(
            duration + MIC_GAP_WARN_NS + 50_000_000,
            duration,
        )

        self.assertEqual(recorder.mic_gap_count, 1)
        self.assertEqual(
            recorder.mic_max_gap_ns,
            MIC_GAP_WARN_NS + 50_000_000,
        )

    def test_invalid_pts_and_discontinuity_are_counted(self):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        recorder._observe_mic_timing(None, None, discont=True)

        self.assertEqual(recorder.mic_buffer_count, 1)
        self.assertEqual(recorder.mic_invalid_pts_count, 1)
        self.assertEqual(recorder.mic_discont_count, 1)


class RecorderStopTests(unittest.TestCase):
    @patch(
        "troika_d_lite.recorder.GLib.timeout_add_seconds",
        return_value=123,
    )
    def test_stop_pushes_eos_to_screen_and_microphone(self, _timeout):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _Pipeline(include_mic=True)
        recorder.pipeline = pipeline

        recorder.stop()

        self.assertEqual(pipeline.screen.pad.events, 1)
        self.assertEqual(pipeline.mic.pad.events, 1)
        self.assertEqual(pipeline.fallback_events, 0)
        self.assertEqual(recorder.stop_timeout_id, 123)

    @patch(
        "troika_d_lite.recorder.GLib.timeout_add_seconds",
        return_value=123,
    )
    def test_stop_pushes_eos_to_screen_and_system_audio(self, _timeout):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _Pipeline(include_system=True)
        recorder.pipeline = pipeline

        recorder.stop()

        self.assertEqual(pipeline.screen.pad.events, 1)
        self.assertEqual(pipeline.system.pad.events, 1)
        self.assertEqual(pipeline.fallback_events, 0)
        self.assertEqual(recorder.stop_timeout_id, 123)

    @patch(
        "troika_d_lite.recorder.GLib.timeout_add_seconds",
        return_value=123,
    )
    def test_stop_pushes_eos_to_all_dual_audio_sources(self, _timeout):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _Pipeline(include_mic=True, include_system=True)
        recorder.pipeline = pipeline

        recorder.stop()

        self.assertEqual(pipeline.screen.pad.events, 1)
        self.assertEqual(pipeline.mic.pad.events, 1)
        self.assertEqual(pipeline.system.pad.events, 1)
        self.assertEqual(pipeline.fallback_events, 0)
        self.assertEqual(recorder.stop_timeout_id, 123)

    @patch(
        "troika_d_lite.recorder.GLib.timeout_add_seconds",
        return_value=123,
    )
    def test_video_only_stop_still_uses_screen_source(self, _timeout):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _Pipeline()
        recorder.pipeline = pipeline

        recorder.stop()

        self.assertEqual(pipeline.screen.pad.events, 1)
        self.assertEqual(pipeline.fallback_events, 0)


if __name__ == "__main__":
    unittest.main()
