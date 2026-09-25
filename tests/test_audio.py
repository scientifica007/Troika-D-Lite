import json
import unittest
from unittest.mock import patch

from troika_d_lite.audio import (
    MicrophoneSource,
    SystemAudioSource,
    default_microphone_source,
    default_system_audio_source,
    list_microphones,
    list_system_audio_sources,
)


class AudioDiscoveryTests(unittest.TestCase):
    @patch("troika_d_lite.audio.shutil.which", return_value="/usr/bin/pactl")
    @patch("troika_d_lite.audio._run")
    def test_json_discovery_splits_microphones_and_monitors(self, run, _which):
        payload = [
            {
                "name": "alsa_input.usb-mic",
                "description": "USB Microphone",
                "monitor_of_sink": None,
                "properties": {},
            },
            {
                "name": "alsa_output.pci.monitor",
                "description": "Built-in Audio Monitor",
                "monitor_of_sink": 2,
                "properties": {"device.class": "monitor"},
            },
        ]
        run.return_value = json.dumps(payload)

        self.assertEqual(
            list_microphones(),
            [
                MicrophoneSource(
                    name="alsa_input.usb-mic",
                    description="USB Microphone",
                )
            ],
        )
        self.assertEqual(
            list_system_audio_sources(),
            [
                SystemAudioSource(
                    name="alsa_output.pci.monitor",
                    description="Built-in Audio Monitor",
                )
            ],
        )

    @patch("troika_d_lite.audio._run")
    def test_default_microphone_prefers_pactl_default(self, run):
        microphones = [
            MicrophoneSource("mic.internal", "Internal"),
            MicrophoneSource("mic.usb", "USB"),
        ]
        run.return_value = "mic.usb\n"
        self.assertEqual(
            default_microphone_source(microphones),
            "mic.usb",
        )

    @patch("troika_d_lite.audio._run", return_value="")
    def test_default_microphone_falls_back_to_first_available(self, _run):
        microphones = [
            MicrophoneSource("mic.internal", "Internal"),
            MicrophoneSource("mic.usb", "USB"),
        ]
        self.assertEqual(
            default_microphone_source(microphones),
            "mic.internal",
        )

    @patch("troika_d_lite.audio._run")
    def test_default_system_audio_uses_default_sink_monitor(self, run):
        sources = [
            SystemAudioSource("sink.other.monitor", "Other"),
            SystemAudioSource("sink.default.monitor", "Default"),
        ]
        run.return_value = "sink.default\n"
        self.assertEqual(
            default_system_audio_source(sources),
            "sink.default.monitor",
        )

    @patch("troika_d_lite.audio._run", return_value="")
    def test_default_system_audio_falls_back_to_first_monitor(self, _run):
        sources = [
            SystemAudioSource("sink.a.monitor", "A"),
            SystemAudioSource("sink.b.monitor", "B"),
        ]
        self.assertEqual(
            default_system_audio_source(sources),
            "sink.a.monitor",
        )


if __name__ == "__main__":
    unittest.main()
