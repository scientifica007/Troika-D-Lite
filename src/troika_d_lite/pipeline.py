from dataclasses import dataclass
from pathlib import Path
from typing import Optional


AUDIO_BUFFER_US = 500_000
AUDIO_LATENCY_US = 20_000
AUDIO_QUEUE_NS = 3_000_000_000
AUDIO_RATE_HZ = 48_000
AUDIO_BITRATE_BPS = 128_000
AUDIO_MIXER_LATENCY_MS = 100

VIDEO_CAPTURE_QUEUE_NS = 1_000_000_000
VIDEO_MUX_QUEUE_NS = 3_000_000_000

ROBUST_MP4_MAX_DURATION_NS = 86_400_000_000_000
ROBUST_MP4_UPDATE_PERIOD_NS = 1_000_000_000

VIDEO_BITRATE_KBPS = 4500
X264_SPEED_PRESET = "veryfast"
X264_KEY_INT_MAX = 60

REQUIRED_VIDEO_GST_ELEMENTS = (
    "pipewiresrc",
    "queue",
    "videoconvert",
    "videorate",
    "imagefreeze",
    "videoscale",
    "x264enc",
    "h264parse",
    "mp4mux",
    "filesink",
)

REQUIRED_AUDIO_GST_ELEMENTS = (
    "pulsesrc",
    "audioconvert",
    "audioresample",
    "avenc_aac",
)

REQUIRED_DUAL_AUDIO_GST_ELEMENTS = (
    "audiomixer",
)

# Compatibility name retained for callers/tests that refer to the L2 name.
REQUIRED_MICROPHONE_GST_ELEMENTS = REQUIRED_AUDIO_GST_ELEMENTS


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


def _audio_source(
    device: str,
    source_name: str,
    queue_name: str,
) -> str:
    return (
        f"pulsesrc name={source_name} device={_q(device)} "
        f"buffer-time={AUDIO_BUFFER_US} "
        f"latency-time={AUDIO_LATENCY_US} "
        "provide-clock=false slave-method=resample ! "
        "audioconvert ! audioresample ! "
        f"audio/x-raw,rate={AUDIO_RATE_HZ} ! "
        f"{_queue(queue_name, AUDIO_QUEUE_NS)}"
    )


def _audio_chain(
    microphone_device: Optional[str],
    system_audio_device: Optional[str],
) -> str:
    sources = []
    if microphone_device is not None:
        sources.append(
            (
                microphone_device,
                "mic_src",
                "mic_capture_q",
            )
        )
    if system_audio_device is not None:
        sources.append(
            (
                system_audio_device,
                "system_audio_src",
                "system_capture_q",
            )
        )

    if not sources:
        return ""

    mux_queue = _queue("audio_mux_q", AUDIO_QUEUE_NS)
    encoder = f"avenc_aac bitrate={AUDIO_BITRATE_BPS}"

    if len(sources) == 1:
        device, source_name, queue_name = sources[0]
        return (
            f"{_audio_source(device, source_name, queue_name)} ! "
            f"{encoder} ! {mux_queue} ! mux. "
        )

    branches = " ".join(
        f"{_audio_source(device, source_name, queue_name)} ! amix."
        for device, source_name, queue_name in sources
    )
    return (
        f"{branches} "
        f"audiomixer name=amix latency={AUDIO_MIXER_LATENCY_MS} ! "
        "audioconvert ! audioresample ! "
        f"audio/x-raw,rate={AUDIO_RATE_HZ} ! "
        f"{encoder} ! {mux_queue} ! mux. "
    )


def build_video_pipeline(
    stream: VideoStream,
    fps: int,
    output_path: Path,
    microphone_device: Optional[str] = None,
    system_audio_device: Optional[str] = None,
) -> PipelinePlan:
    if fps not in (15, 30):
        raise ValueError("Troika D Lite v0.1 supports only 15 or 30 FPS")
    if microphone_device is not None and not microphone_device.strip():
        raise ValueError("Microphone device cannot be empty")
    if system_audio_device is not None and not system_audio_device.strip():
        raise ValueError("System-audio device cannot be empty")

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

    audio_chain = _audio_chain(
        microphone_device,
        system_audio_device,
    )
    include_audio = (
        microphone_device is not None
        or system_audio_device is not None
    )

    if include_audio:
        video_rate_chain = (
            "imagefreeze name=video_hold "
            "is-live=true allow-replace=true ! "
            f"video/x-raw,framerate={fps}/1 ! "
            "videorate name=video_rate skip-to-first=true ! "
            f"video/x-raw,framerate={fps}/1 ! "
        )
    else:
        video_rate_chain = (
            "videorate name=video_rate skip-to-first=true ! "
            f"video/x-raw,framerate={fps}/1 ! "
        )

    description = (
        f"{_video_source(stream)} ! "
        f"{video_capture_q} ! "
        "videoconvert ! video/x-raw,format=I420 ! "
        f"{video_rate_chain}"
        "videoscale ! "
        f"x264enc bitrate={VIDEO_BITRATE_KBPS} "
        f"speed-preset={X264_SPEED_PRESET} "
        f"tune=zerolatency key-int-max={X264_KEY_INT_MAX} ! "
        "h264parse ! "
        f"{video_mux_q} ! mux. "
        f"{audio_chain}"
        f"{robust_mux} ! "
        f"filesink location={_q(str(output_path))}"
    )

    return PipelinePlan(description=description)
