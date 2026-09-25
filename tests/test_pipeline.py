import unittest
from pathlib import Path

from troika_d_lite.pipeline import (
    AUDIO_BITRATE_BPS,
    AUDIO_RATE_HZ,
    ROBUST_MP4_MAX_DURATION_NS,
    ROBUST_MP4_UPDATE_PERIOD_NS,
    VideoStream,
    build_video_pipeline,
)


class PipelineTests(unittest.TestCase):
    def test_modern_portal_stream_uses_pipewire_serial(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77, pipewire_serial=12345),
            30,
            Path("/tmp/a.mp4"),
        )
        self.assertIn("pipewiresrc name=screen_src", plan.description)
        self.assertIn("fd=9", plan.description)
        self.assertIn('target-object="12345"', plan.description)
        self.assertNotIn('path="77"', plan.description)

    def test_legacy_portal_stream_uses_node_id(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            15,
            Path("/tmp/a.mp4"),
        )
        self.assertIn('path="77"', plan.description)
        self.assertNotIn("target-object=", plan.description)

    def test_only_15_and_30_fps_are_allowed(self):
        for fps in (15, 30):
            plan = build_video_pipeline(
                VideoStream(fd=9, node_id=77),
                fps,
                Path("/tmp/a.mp4"),
            )
            self.assertIn(
                f"video/x-raw,framerate={fps}/1",
                plan.description,
            )

        with self.assertRaises(ValueError):
            build_video_pipeline(
                VideoStream(fd=9, node_id=77),
                60,
                Path("/tmp/a.mp4"),
            )

    def test_full_screen_chain_keeps_field_baseline_order(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            30,
            Path("/tmp/a.mp4"),
        )
        convert_index = plan.description.index(
            "videoconvert ! video/x-raw,format=I420"
        )
        rate_index = plan.description.index(
            "videorate name=video_rate skip-to-first=true"
        )
        self.assertLess(convert_index, rate_index)

    def test_mp4_uses_robust_periodic_moov_updates(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            30,
            Path("/tmp/a.mp4"),
        )
        self.assertIn(
            f"reserved-max-duration={ROBUST_MP4_MAX_DURATION_NS}",
            plan.description,
        )
        self.assertIn(
            "reserved-moov-update-period="
            f"{ROBUST_MP4_UPDATE_PERIOD_NS}",
            plan.description,
        )

    def test_microphone_path_remains_field_baseline(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            30,
            Path("/tmp/a.mp4"),
            microphone_device="alsa_input.usb-test",
        )
        self.assertIn("pulsesrc name=mic_src", plan.description)
        self.assertIn('device="alsa_input.usb-test"', plan.description)
        self.assertIn("provide-clock=false", plan.description)
        self.assertIn("slave-method=resample", plan.description)
        self.assertIn(
            f"audio/x-raw,rate={AUDIO_RATE_HZ}",
            plan.description,
        )
        self.assertIn(
            f"avenc_aac bitrate={AUDIO_BITRATE_BPS}",
            plan.description,
        )
        self.assertNotIn("audiomixer", plan.description)

    def test_system_audio_path_uses_monitor_source_and_aac(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            30,
            Path("/tmp/a.mp4"),
            system_audio_device="alsa_output.pci.monitor",
        )
        self.assertIn(
            "pulsesrc name=system_audio_src",
            plan.description,
        )
        self.assertIn(
            'device="alsa_output.pci.monitor"',
            plan.description,
        )
        self.assertIn("system_capture_q", plan.description)
        self.assertIn("provide-clock=false", plan.description)
        self.assertIn("slave-method=resample", plan.description)
        self.assertIn(
            f"avenc_aac bitrate={AUDIO_BITRATE_BPS}",
            plan.description,
        )
        self.assertNotIn("audiomixer", plan.description)

    def test_l3_rejects_dual_audio_until_l4(self):
        with self.assertRaises(ValueError):
            build_video_pipeline(
                VideoStream(fd=9, node_id=77),
                30,
                Path("/tmp/a.mp4"),
                microphone_device="mic.test",
                system_audio_device="sink.monitor",
            )

    def test_video_only_path_contains_no_audio_elements(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            30,
            Path("/tmp/a.mp4"),
        )
        self.assertNotIn("pulsesrc", plan.description)
        self.assertNotIn("avenc_aac", plan.description)

    def test_l3_contains_no_out_of_scope_media_paths(self):
        plan = build_video_pipeline(
            VideoStream(fd=9, node_id=77),
            30,
            Path("/tmp/a.mp4"),
            system_audio_device="sink.monitor",
        )
        for forbidden in (
            "ximagesrc",
            "v4l2src",
            "compositor",
            "videocrop",
            "audiomixer",
            "vp8enc",
            "webmmux",
        ):
            self.assertNotIn(forbidden, plan.description)


if __name__ == "__main__":
    unittest.main()
