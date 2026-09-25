#!/usr/bin/env python3
"""Interactive, repeatable performance benchmark for GTK recorder sessions."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


MEDIA_SUFFIXES = {".mp4", ".webm", ".mkv"}
CLK_TCK = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


@dataclass
class ProcSample:
    at: float
    cpu_ticks: int
    rss_kib: int


@dataclass
class LogState:
    lock: threading.Lock
    eos_request_at: Optional[float] = None
    finalization_end_at: Optional[float] = None
    finalization_outcome: Optional[str] = None
    video_timing_line: Optional[str] = None


def read_proc_sample(pid: int) -> Optional[ProcSample]:
    stat_path = Path(f"/proc/{pid}/stat")
    status_path = Path(f"/proc/{pid}/status")
    try:
        stat = stat_path.read_text(encoding="utf-8")
        right = stat.rfind(")")
        fields = stat[right + 2 :].split()
        cpu_ticks = int(fields[11]) + int(fields[12])

        rss_kib = 0
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                rss_kib = int(line.split()[1])
                break
        return ProcSample(time.monotonic(), cpu_ticks, rss_kib)
    except (FileNotFoundError, ProcessLookupError, ValueError, IndexError):
        return None


def cpu_percent(previous: ProcSample, current: ProcSample) -> float:
    wall = current.at - previous.at
    if wall <= 0:
        return 0.0
    cpu_seconds = (current.cpu_ticks - previous.cpu_ticks) / CLK_TCK
    return max(0.0, 100.0 * cpu_seconds / wall)


def summarize_samples(samples: list[ProcSample]) -> dict:
    if not samples:
        return {
            "sample_count": 0,
            "cpu_mean_pct": None,
            "cpu_peak_pct": None,
            "rss_mean_mib": None,
            "rss_peak_mib": None,
        }

    cpu_values = [
        cpu_percent(a, b)
        for a, b in zip(samples, samples[1:])
    ]
    rss_mib = [sample.rss_kib / 1024.0 for sample in samples]
    return {
        "sample_count": len(samples),
        "cpu_mean_pct": (
            round(statistics.fmean(cpu_values), 3)
            if cpu_values
            else 0.0
        ),
        "cpu_peak_pct": (
            round(max(cpu_values), 3)
            if cpu_values
            else 0.0
        ),
        "rss_mean_mib": round(statistics.fmean(rss_mib), 3),
        "rss_peak_mib": round(max(rss_mib), 3),
    }


def dbus_name_has_owner(app_id: str) -> bool:
    try:
        proc = subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.freedesktop.DBus",
                "--object-path",
                "/org/freedesktop/DBus",
                "--method",
                "org.freedesktop.DBus.NameHasOwner",
                app_id,
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and "true" in proc.stdout.lower()


def wait_for_dbus_owner(
    app_id: str,
    started_at: float,
    timeout: float,
) -> float:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if dbus_name_has_owner(app_id):
            return (time.monotonic() - started_at) * 1000.0
        time.sleep(0.05)
    raise RuntimeError(
        f"Application did not own D-Bus name {app_id!r} within {timeout}s"
    )


def media_snapshot(directory: Path) -> dict[Path, int]:
    if not directory.exists():
        return {}
    result = {}
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES:
            try:
                result[path] = path.stat().st_mtime_ns
            except FileNotFoundError:
                pass
    return result


def find_new_media(
    directory: Path,
    before: dict[Path, int],
    not_before_ns: int,
) -> Optional[Path]:
    candidates = []
    for path, mtime in media_snapshot(directory).items():
        old_mtime = before.get(path)
        if (
            path not in before
            or (old_mtime is not None and mtime > old_mtime)
        ) and mtime >= not_before_ns:
            candidates.append((mtime, path))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def collect_for(
    pid: int,
    seconds: float,
    interval: float,
) -> list[ProcSample]:
    samples = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        sample = read_proc_sample(pid)
        if sample is None:
            break
        samples.append(sample)
        time.sleep(interval)
    sample = read_proc_sample(pid)
    if sample is not None:
        samples.append(sample)
    return samples


def start_log_reader(
    process: subprocess.Popen,
    log_path: Path,
    state: LogState,
) -> threading.Thread:
    def reader() -> None:
        assert process.stdout is not None
        with log_path.open("w", encoding="utf-8") as handle:
            for raw in process.stdout:
                line = raw.rstrip("\n")
                now = time.monotonic()
                handle.write(line + "\n")
                handle.flush()
                print(f"[app] {line}", flush=True)
                with state.lock:
                    if "EOS request:" in line:
                        state.eos_request_at = now
                    if "Video timing stats [eos]" in line:
                        state.finalization_end_at = now
                        state.finalization_outcome = "eos"
                        state.video_timing_line = line
                    elif "Video timing stats [finalize-timeout]" in line:
                        state.finalization_end_at = now
                        state.finalization_outcome = "finalize-timeout"
                        state.video_timing_line = line
                    elif "Video timing stats [external-portal-stop]" in line:
                        state.finalization_end_at = now
                        state.finalization_outcome = "external-portal-stop"
                        state.video_timing_line = line

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    return thread


def notify(message: str) -> None:
    if subprocess.run(
        ["which", "notify-send"],
        capture_output=True,
        check=False,
    ).returncode == 0:
        subprocess.run(
            ["notify-send", "Troika benchmark", message],
            check=False,
        )
    print("\a" + message, flush=True)


def wait_for_new_media(
    directory: Path,
    before: dict[Path, int],
    launch_wall_ns: int,
    process: subprocess.Popen,
) -> Path:
    print(
        "\nConfigure the requested scenario, click Start/Share, "
        "then leave the workload running.",
        flush=True,
    )
    while process.poll() is None:
        path = find_new_media(directory, before, launch_wall_ns)
        if path is not None:
            return path
        time.sleep(0.2)
    raise RuntimeError("Application exited before a recording file appeared")


def wait_for_eos_request(
    process: subprocess.Popen,
    state: LogState,
    timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        with state.lock:
            if state.eos_request_at is not None:
                return
        time.sleep(0.05)
    raise RuntimeError("No EOS request observed after the recording window")


def wait_for_finalization(
    process: subprocess.Popen,
    state: LogState,
    timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        with state.lock:
            if state.finalization_end_at is not None:
                return
        time.sleep(0.05)
    raise RuntimeError("No finalization outcome observed")


def terminate_after_benchmark(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure one interactive recorder session: startup, idle CPU/RSS, "
            "recording CPU/RSS, finalization, and recorder timing diagnostics."
        )
    )
    parser.add_argument("--app", required=True, help="Short app key")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Videos",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("benchmark-results"),
    )
    parser.add_argument("--idle-seconds", type=float, default=10.0)
    parser.add_argument("--record-seconds", type=float, default=60.0)
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--stop-timeout", type=float, default=60.0)
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command after --",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise SystemExit("A command is required after --")
    if not args.cwd.is_dir():
        raise SystemExit(f"Working directory not found: {args.cwd}")
    if not shutil_which("gdbus"):
        raise SystemExit(
            "gdbus is required for startup timing "
            "(Ubuntu package: libglib2.0-bin)"
        )
    if dbus_name_has_owner(args.app_id):
        raise SystemExit(
            f"{args.app_id} is already running; close it before benchmarking"
        )

    args.results_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    stem = f"{args.app}__{args.scenario}__{stamp}"
    log_path = args.results_dir / f"{stem}.log"
    json_path = args.results_dir / f"{stem}.json"

    output_before = media_snapshot(args.output_dir)
    launch_wall_ns = time.time_ns()
    started_at = time.monotonic()

    print("Launching:", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        cwd=args.cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    state = LogState(lock=threading.Lock())
    log_thread = start_log_reader(process, log_path, state)

    try:
        startup_ms = wait_for_dbus_owner(
            args.app_id,
            started_at,
            args.startup_timeout,
        )
        print(f"Startup proxy: {startup_ms:.1f} ms", flush=True)

        print(
            f"Collecting idle baseline for {args.idle_seconds:.0f}s...",
            flush=True,
        )
        idle_samples = collect_for(
            process.pid,
            args.idle_seconds,
            args.sample_interval,
        )

        media_path = wait_for_new_media(
            args.output_dir,
            output_before,
            launch_wall_ns,
            process,
        )
        print(f"Recording detected: {media_path}", flush=True)

        print(
            f"Collecting recording load for {args.record_seconds:.0f}s...",
            flush=True,
        )
        recording_samples = collect_for(
            process.pid,
            args.record_seconds,
            args.sample_interval,
        )

        notify("Measurement window complete — click Stop Recording now.")
        wait_for_eos_request(process, state, args.stop_timeout)
        wait_for_finalization(process, state, 20.0)

        with state.lock:
            if (
                state.eos_request_at is not None
                and state.finalization_end_at is not None
            ):
                finalization_ms = (
                    state.finalization_end_at - state.eos_request_at
                ) * 1000.0
            else:
                finalization_ms = None
            outcome = state.finalization_outcome
            timing_line = state.video_timing_line

        result = {
            "schema": 1,
            "app": args.app,
            "scenario": args.scenario,
            "app_id": args.app_id,
            "command": command,
            "cwd": str(args.cwd),
            "output_file": str(media_path),
            "startup_proxy_ms": round(startup_ms, 3),
            "idle": summarize_samples(idle_samples),
            "recording": summarize_samples(recording_samples),
            "finalization_ms": (
                round(finalization_ms, 3)
                if finalization_ms is not None
                else None
            ),
            "finalization_outcome": outcome,
            "video_timing_line": timing_line,
            "sample_interval_seconds": args.sample_interval,
            "idle_seconds_requested": args.idle_seconds,
            "record_seconds_requested": args.record_seconds,
            "log_file": str(log_path),
        }
        json_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        print("\nBenchmark result:")
        print(json.dumps(result, indent=2, sort_keys=True))
        print(f"\nSaved: {json_path}")
        return 0
    finally:
        terminate_after_benchmark(process)
        log_thread.join(timeout=2)


def shutil_which(command: str) -> Optional[str]:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
