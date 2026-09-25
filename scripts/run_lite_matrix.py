#!/usr/bin/env python3
"""Run the complete eight-case Troika D Lite performance sweep."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "scripts" / "benchmark_session.py"
SUMMARIZER = ROOT / "scripts" / "summarize_benchmarks.py"

SCENARIOS = (
    ("matrix-15-m0-s0-low", 15, 0, 0, "low"),
    ("matrix-15-m1-s0-low", 15, 1, 0, "low"),
    ("matrix-15-m0-s1-low", 15, 0, 1, "low"),
    ("matrix-15-m1-s1-high", 15, 1, 1, "high"),
    ("matrix-30-m0-s0-low", 30, 0, 0, "low"),
    ("matrix-30-m1-s0-low", 30, 1, 0, "low"),
    ("matrix-30-m0-s1-low", 30, 0, 1, "low"),
    ("matrix-30-m1-s1-high", 30, 1, 1, "high"),
)


def successful_scenarios(results_dir: Path) -> set[str]:
    completed: set[str] = set()
    if not results_dir.exists():
        return completed

    for path in results_dir.glob("lite__matrix-*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            payload.get("app") == "lite"
            and payload.get("finalization_outcome") == "eos"
            and isinstance(payload.get("scenario"), str)
        ):
            completed.add(payload["scenario"])
    return completed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the eight required Troika D Lite FPS/audio performance "
            "cases interactively, with resume-safe result detection."
        )
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=ROOT,
        help="Troika D Lite working tree.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Videos",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "benchmark-results" / "lite-matrix",
    )
    parser.add_argument("--idle-seconds", type=float, default=10.0)
    parser.add_argument("--record-seconds", type=float, default=30.0)
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument(
        "--rerun-completed",
        action="store_true",
        help="Run cases again even when a successful JSON already exists.",
    )
    return parser.parse_args()


def run_case(args: argparse.Namespace, case) -> int:
    scenario, fps, mic, system_audio, workload = case
    command = [
        sys.executable,
        str(BENCHMARK),
        "--app",
        "lite",
        "--scenario",
        scenario,
        "--fps",
        str(fps),
        "--mic",
        str(mic),
        "--system-audio",
        str(system_audio),
        "--workload",
        workload,
        "--app-id",
        "io.github.scientifica007.TroikaDLite",
        "--cwd",
        str(args.cwd),
        "--output-dir",
        str(args.output_dir),
        "--results-dir",
        str(args.results_dir),
        "--idle-seconds",
        str(args.idle_seconds),
        "--record-seconds",
        str(args.record_seconds),
        "--sample-interval",
        str(args.sample_interval),
        "--",
        "env",
        "PYTHONPATH=src",
        "/usr/bin/python3",
        "-m",
        "troika_d_lite",
    ]
    return subprocess.run(command, check=False).returncode


def summarize(results_dir: Path) -> int:
    files = sorted(
        path
        for path in results_dir.glob("*.json")
        if path.name != "summary.json"
    )
    if not files:
        print("No matrix JSON results found.", file=sys.stderr)
        return 1

    command = [
        sys.executable,
        str(SUMMARIZER),
        *[str(path) for path in files],
        "--require-lite-matrix",
        "--json-out",
        str(results_dir / "summary.json"),
    ]
    return subprocess.run(command, check=False).returncode


def main() -> int:
    args = parse_args()
    args.cwd = args.cwd.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.results_dir = args.results_dir.expanduser().resolve()

    if not args.cwd.is_dir():
        raise SystemExit(f"Working directory not found: {args.cwd}")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    completed = successful_scenarios(args.results_dir)

    print("Troika D Lite — L7 eight-case performance sweep")
    print(f"Results: {args.results_dir}")
    print(
        "Each case measures idle first. Configure the UI only after the "
        "benchmark asks you to configure the requested scenario."
    )

    for index, case in enumerate(SCENARIOS, start=1):
        scenario, fps, mic, system_audio, workload = case
        if scenario in completed and not args.rerun_completed:
            print(f"\n[{index}/8] SKIP already successful: {scenario}")
            continue

        print("\n" + "=" * 68)
        print(f"[{index}/8] {scenario}")
        print(
            f"Set after idle: FPS={fps}, microphone={'ON' if mic else 'OFF'}, "
            f"system audio={'ON' if system_audio else 'OFF'}"
        )
        if workload == "high":
            print(
                "Workload: use the same local moving-media/desktop-motion "
                "workload for every HIGH case."
            )
        else:
            print("Workload: keep the desktop mostly static (LOW).")

        answer = input(
            "Press Enter to launch this case, or type q then Enter to stop: "
        ).strip().lower()
        if answer == "q":
            print("Sweep paused. Existing successful results are preserved.")
            return 0

        rc = run_case(args, case)
        if rc != 0:
            print(
                f"Case failed with exit status {rc}: {scenario}",
                file=sys.stderr,
            )
            return rc

        completed = successful_scenarios(args.results_dir)
        if scenario not in completed:
            print(
                f"No successful EOS JSON was recorded for {scenario}.",
                file=sys.stderr,
            )
            return 1

    print("\nAll eight cases have successful EOS results.")
    rc = summarize(args.results_dir)
    if rc == 0:
        print(f"Summary: {args.results_dir / 'summary.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
