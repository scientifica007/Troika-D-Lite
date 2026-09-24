from dataclasses import dataclass
from pathlib import Path
from typing import Optional


VIDEO_CAPTURE_QUEUE_NS = 1_000_000_000
VIDEO_MUX_QUEUE_NS = 3_000_000_000

ROBUST_MP4_MAX_DURATION_NS = 86_400_000_000_000
ROBUST_MP4_UPDATE_PERIOD_NS = 1_000_000_000

VIDEO_BITRATE_KBPS = 4500
X264_SPEED_PRESET = "veryfast"
X264_KEY_INT_MAX = 60

REQUIRED_GST_ELEMENTS = (
    "pipewiresrc",
    "queue",
    "videoconvert",
    "videorate",
    "videoscale",
    "x264enc",
    "h264parse",
    "mp4mux",
    "filesink",
)


@dataclass(frozen=True)
class VideoStream:
    fd: int
    node_id: int
    pipewire_serial: Optional[int] = None


@dataclass(frozen=True)
class PipelinePlan:
    description: str
    encoder: str = "x264/H.264"
    extension: str = "mp4"


def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _queue(name: str, max_time_ns: int, leaky: Optional[str] = None) -> str:
    value = (
        f"queue name={name} max-size-buffers=0 max-size-bytes=0 "
        f"max-size-time={max_time_ns}"
    )
    if leaky:
        value += f" leaky={leaky}"
    return value


def _video_source(stream: VideoStream) -> str:
    if stream.pipewire_serial is not None:
        selector = f"target-object={_q(str(stream.pipewire_serial))}"
    else:
        selector = f"path={_q(str(stream.node_id))}"

    return (
        f"pipewiresrc name=screen_src fd={stream.fd} "
        f"{selector} do-timestamp=true"
    )


def build_video_pipeline(
    stream: VideoStream,
    fps: int,
    output_path: Path,
) -> PipelinePlan:
    if fps not in (15, 30):
        raise ValueError("Troika D Lite v0.1 supports only 15 or 30 FPS")

    video_capture_q = _queue(
        "video_capture_q",
        VIDEO_CAPTURE_QUEUE_NS,
        "downstream",
    )
    video_mux_q = _queue("video_mux_q", VIDEO_MUX_QUEUE_NS)

    robust_mux = (
        "mp4mux name=mux "
        f"reserved-max-duration={ROBUST_MP4_MAX_DURATION_NS} "
        f"reserved-moov-update-period={ROBUST_MP4_UPDATE_PERIOD_NS}"
    )

    description = (
        f"{_video_source(stream)} ! "
        f"{video_capture_q} ! "
        "videoconvert ! video/x-raw,format=I420 ! "
        "videorate name=video_rate skip-to-first=true ! "
        f"video/x-raw,framerate={fps}/1 ! "
        "videoscale ! "
        f"x264enc bitrate={VIDEO_BITRATE_KBPS} "
        f"speed-preset={X264_SPEED_PRESET} "
        f"tune=zerolatency key-int-max={X264_KEY_INT_MAX} ! "
        "h264parse ! "
        f"{video_mux_q} ! mux. "
        f"{robust_mux} ! "
        f"filesink location={_q(str(output_path))}"
    )

    return PipelinePlan(description=description)
