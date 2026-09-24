import unittest
from unittest.mock import patch

from troika_d_lite.recorder import Recorder


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


class _Pipeline:
    def __init__(self, include_mic):
        self.screen = _Source()
        self.mic = _Source() if include_mic else None
        self.fallback_events = 0

    def get_by_name(self, name):
        if name == "screen_src":
            return self.screen
        if name == "mic_src":
            return self.mic
        return None

    def send_event(self, _event):
        self.fallback_events += 1
        return True


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
    def test_video_only_stop_still_uses_screen_source(self, _timeout):
        recorder = Recorder(lambda _text: None, lambda _active: None)
        pipeline = _Pipeline(include_mic=False)
        recorder.pipeline = pipeline

        recorder.stop()

        self.assertEqual(pipeline.screen.pad.events, 1)
        self.assertEqual(pipeline.fallback_events, 0)


if __name__ == "__main__":
    unittest.main()
