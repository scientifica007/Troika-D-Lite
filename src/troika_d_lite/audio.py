import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MicrophoneSource:
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


def list_microphones() -> List[MicrophoneSource]:
    if not shutil.which("pactl"):
        return []

    output = _run("pactl", "--format=json", "list", "sources")
    if output:
        try:
            payload = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            payload = []

        result: List[MicrophoneSource] = []
        for item in payload:
            name = str(item.get("name") or "").strip()
            if not name or _is_monitor(item):
                continue
            properties = item.get("properties") or {}
            description = (
                item.get("description")
                or properties.get("device.description")
                or properties.get("device.product.name")
                or name
            )
            result.append(
                MicrophoneSource(
                    name=name,
                    description=str(description),
                )
            )
        if result:
            return result

    # Compatibility fallback for pactl variants without JSON support.
    fallback = _run("pactl", "list", "short", "sources")
    result = []
    for line in fallback.splitlines():
        columns = line.split("\t")
        if len(columns) < 2:
            columns = line.split()
        if len(columns) < 2:
            continue
        name = columns[1].strip()
        if not name or name.endswith(".monitor"):
            continue
        result.append(MicrophoneSource(name=name, description=name))
    return result


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
