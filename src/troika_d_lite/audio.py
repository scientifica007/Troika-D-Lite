import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MicrophoneSource:
    name: str
    description: str


@dataclass(frozen=True)
class SystemAudioSource:
    name: str
    description: str


def _run(*args: str) -> str:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def _is_monitor(item: dict) -> bool:
    name = str(item.get("name") or "")
    properties = item.get("properties") or {}
    monitor_of_sink = item.get("monitor_of_sink")
    return (
        monitor_of_sink not in (None, "", False)
        or name.endswith(".monitor")
        or properties.get("device.class") == "monitor"
    )


def _source_description(item: dict, name: str) -> str:
    properties = item.get("properties") or {}
    return str(
        item.get("description")
        or properties.get("device.description")
        or properties.get("device.product.name")
        or name
    )


def _json_source_items() -> List[dict]:
    output = _run("pactl", "--format=json", "list", "sources")
    if not output:
        return []
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return []
    return payload if isinstance(payload, list) else []


def _fallback_source_names() -> List[str]:
    output = _run("pactl", "list", "short", "sources")
    names = []
    for line in output.splitlines():
        columns = line.split("\t")
        if len(columns) < 2:
            columns = line.split()
        if len(columns) < 2:
            continue
        name = columns[1].strip()
        if name:
            names.append(name)
    return names


def list_microphones() -> List[MicrophoneSource]:
    if not shutil.which("pactl"):
        return []

    items = _json_source_items()
    if items:
        result = []
        for item in items:
            name = str(item.get("name") or "").strip()
            if not name or _is_monitor(item):
                continue
            result.append(
                MicrophoneSource(
                    name=name,
                    description=_source_description(item, name),
                )
            )
        if result:
            return result

    return [
        MicrophoneSource(name=name, description=name)
        for name in _fallback_source_names()
        if not name.endswith(".monitor")
    ]


def list_system_audio_sources() -> List[SystemAudioSource]:
    if not shutil.which("pactl"):
        return []

    items = _json_source_items()
    if items:
        result = []
        for item in items:
            name = str(item.get("name") or "").strip()
            if not name or not _is_monitor(item):
                continue
            result.append(
                SystemAudioSource(
                    name=name,
                    description=_source_description(item, name),
                )
            )
        if result:
            return result

    return [
        SystemAudioSource(name=name, description=name)
        for name in _fallback_source_names()
        if name.endswith(".monitor")
    ]


def default_microphone_source(
    microphones: List[MicrophoneSource],
) -> Optional[str]:
    if not microphones:
        return None

    available = {source.name for source in microphones}
    default = _run("pactl", "get-default-source").strip()
    if not default:
        info = _run("pactl", "info")
        for line in info.splitlines():
            if line.lower().startswith("default source:"):
                default = line.split(":", 1)[1].strip()
                break

    if default in available:
        return default
    return microphones[0].name


def default_system_audio_source(
    sources: List[SystemAudioSource],
) -> Optional[str]:
    if not sources:
        return None

    available = {source.name for source in sources}
    sink = _run("pactl", "get-default-sink").strip()
    if not sink:
        info = _run("pactl", "info")
        for line in info.splitlines():
            if line.lower().startswith("default sink:"):
                sink = line.split(":", 1)[1].strip()
                break

    if sink:
        candidate = f"{sink}.monitor"
        if candidate in available:
            return candidate

    return sources[0].name
