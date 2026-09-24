import json
import unittest
from unittest.mock import patch

from troika_d_lite.audio import (
    MicrophoneSource,
    default_microphone_source,
    list_microphones,
)


class AudioDiscoveryTests(unittest.TestCase):
    @patch("troika_d_lite.audio.shutil.which", return_value="/usr/bin/pactl")
    @patch("troika_d_lite.audio._run")
    def test_json_discovery_excludes_monitor_sources(self, run, _which):
        payload = [
            {
                "name": "alsa_input.usb-mic",
                "description": "USB Microphone",
                "monitor_of_sink": None,
                "properties": {},
            },
            {
                "name": "alsa_output.pci.monitor",
                "description": "Monitor",
                "monitor_of_sink": 2,
                "properties": {"device.class": "monitor"},
            },
        ]
        run.return_value = json.dumps(payload)

        sources = list_microphones()

        self.assertEqual(
            sources,
            [
                MicrophoneSource(
                    name="alsa_input.usb-mic",
                    description="USB Microphone",
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


if __name__ == "__main__":
    unittest.main()
