#!/usr/bin/env python3
"""Run the controlled Troika D Lite vs Troika D comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "scripts" / "benchmark_session.py"
SUMMARIZER = ROOT / "scripts" / "summarize_benchmarks.py"

LITE_RUNTIME_BASELINE = "00a6ee0d555c4c46b0681fa544588fd44cd2718b"
TROIKA_D_REFERENCE = "cb19f06483c3f3e1641cac025a7683094d839dec"

SCHEDULE = (
    ("A-15-video-low", "lite"),
    ("A-15-video-low", "troika-d"),
    ("A-15-video-low", "troika-d"),
    ("A-15-video-low", "lite"),
    ("A-15-video-low", "lite"),
    ("A-15-video-low", "troika-d"),
    ("B-30-dual-high", "troika-d"),
    ("B-30-dual-high", "lite"),
    ("B-30-dual-high", "lite"),
    ("B-30-dual-high", "troika-d"),
    ("B-30-dual-high", "troika-d"),
    ("B-30-dual-high", "lite"),
)

SCENARIOS = {
    "A-15-video-low": {
        "fps": 15,
        "mic": 0,
        "system_audio": 0,
        "workload": "low",
    },
    "B-30-dual-high": {
        "fps": 30,
        "mic": 1,
        "system_audio": 1,
        "workload": "high",
    },
}

APPS = {
    "lite": {
        "app_id": "io.github.scientifica007.TroikaDLite",
        "module": "troika_d_lite",
    },
    "troika-d": {
        "app_id": "io.github.scientifica007.TroikaD",
        "module": "ubuntu_screen_recorder",
    },
}


def git_output(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise SystemExit(f"Git check failed in {cwd}: {detail}")
    return completed.stdout.strip()


def validate_references(lite_cwd: Path, troika_d_cwd: Path) -> None:
    lite_head = git_output(lite_cwd, "rev-parse", "HEAD")
    if subprocess.run(
        [
            "git",
            "-C",
            str(lite_cwd),
            "diff",
            "--quiet",
            LITE_RUNTIME_BASELINE,
            "--",
            "src",
        ],
        check=False,
    ).returncode != 0:
        raise SystemExit(
            "Lite src/ differs from accepted L6 runtime baseline "
            f"{LITE_RUNTIME_BASELINE}."
        )
    if git_output(lite_cwd, "status", "--porcelain", "--", "src"):
        raise SystemExit(
            "Lite src/ has local changes. Commit/stash/revert them before "
            "the controlled comparison."
        )

    troika_head = git_output(troika_d_cwd, "rev-parse", "HEAD")
    if troika_head != TROIKA_D_REFERENCE:
        raise SystemExit(
            "Troika D checkout is not at the pinned comparison reference.\n"
            f"expected: {TROIKA_D_REFERENCE}\n"
            f"actual:   {troika_head}\n"
            "The runner will not change the checkout automatically."
        )
    if git_output(troika_d_cwd, "status", "--porcelain", "--", "src"):
        raise SystemExit(
            "Troika D src/ has local changes. Preserve or revert them before "
            "benchmarking."
        )

    print(f"Lite checkout:     {lite_head}")
    print(f"Lite runtime base: {LITE_RUNTIME_BASELINE} (src/ unchanged)")
    print(f"Troika D ref:      {troika_head}")


def successful_counts(results_dir: Path) -> Counter:
    counts: Counter = Counter()
    if not results_dir.exists():
        return counts
    for path in results_dir.glob("*.json"):
        if path.name == "summary.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        key = (payload.get("scenario"), payload.get("app"))
        if (
            key[0] in SCENARIOS
            and key[1] in APPS
            and payload.get("finalization_outcome") == "eos"
        ):
            counts[key] += 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run 12 controlled sessions: two scenarios, two applications, "
            "three repetitions each."
        )
    )
    parser.add_argument("--lite-cwd", type=Path, default=ROOT)
    parser.add_argument(
        "--troika-d-cwd",
        type=Path,
        default=Path.home() / "Troika-D",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Videos",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "benchmark-results" / "comparison",
    )
    parser.add_argument("--idle-seconds", type=float, default=10.0)
    parser.add_argument("--record-seconds", type=float, default=60.0)
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument(
        "--rerun-completed",
        action="store_true",
    )
    return parser.parse_args()


def instructions(scenario: str, app: str) -> list[str]:
    cfg = SCENARIOS[scenario]
    lines = [
        f"FPS: {cfg['fps']}",
        f"Microphone: {'ON' if cfg['mic'] else 'OFF'}",
        f"System audio: {'ON' if cfg['system_audio'] else 'OFF'}",
        "Output directory: ~/Videos",
    ]
    if app == "troika-d":
        lines += [
            "Capture mode: Full Screen",
            "Quality profile: Balanced",
            "Webcam: OFF",
        ]
    if cfg["workload"] == "high":
        lines.append(
            "Workload: same local moving-media segment + ordinary desktop "
            "motion used for every B run"
        )
    else:
        lines.append("Workload: mostly static desktop")
    return lines


def run_one(args: argparse.Namespace, scenario: str, app: str) -> int:
    cfg = SCENARIOS[scenario]
    app_cfg = APPS[app]
    cwd = args.lite_cwd if app == "lite" else args.troika_d_cwd
    command = [
        sys.executable,
        str(BENCHMARK),
        "--app", app,
        "--scenario", scenario,
        "--fps", str(cfg["fps"]),
        "--mic", str(cfg["mic"]),
        "--system-audio", str(cfg["system_audio"]),
        "--workload", cfg["workload"],
        "--app-id", app_cfg["app_id"],
        "--cwd", str(cwd),
        "--output-dir", str(args.output_dir),
        "--results-dir", str(args.results_dir),
        "--idle-seconds", str(args.idle_seconds),
        "--record-seconds", str(args.record_seconds),
        "--sample-interval", str(args.sample_interval),
        "--",
        "env", "PYTHONPATH=src", "/usr/bin/python3",
        "-m", app_cfg["module"],
    ]
    return subprocess.run(command, check=False).returncode


def summarize(results_dir: Path) -> int:
    files = sorted(
        p for p in results_dir.glob("*.json")
        if p.name != "summary.json"
    )
    command = [
        sys.executable,
        str(SUMMARIZER),
        *[str(path) for path in files],
        "--require-controlled-comparison",
        "--json-out",
        str(results_dir / "summary.json"),
    ]
    return subprocess.run(command, check=False).returncode


def main() -> int:
    args = parse_args()
    args.lite_cwd = args.lite_cwd.expanduser().resolve()
    args.troika_d_cwd = args.troika_d_cwd.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.results_dir = args.results_dir.expanduser().resolve()

    if not args.lite_cwd.is_dir():
        raise SystemExit(f"Lite checkout not found: {args.lite_cwd}")
    if not args.troika_d_cwd.is_dir():
        raise SystemExit(f"Troika D checkout not found: {args.troika_d_cwd}")

    validate_references(args.lite_cwd, args.troika_d_cwd)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    counts = (
        Counter()
        if args.rerun_completed
        else successful_counts(args.results_dir)
    )
    occurrences: Counter = Counter()

    print("\nTroika D Lite vs Troika D — controlled L7 comparison")
    print(f"Results: {args.results_dir}")
    print("Each app/scenario pair requires 3 successful EOS runs.")
    print("Run order alternates applications to reduce ordering bias.")

    for slot, (scenario, app) in enumerate(SCHEDULE, start=1):
        key = (scenario, app)
        occurrences[key] += 1
        repetition = occurrences[key]

        if counts[key] >= repetition and not args.rerun_completed:
            print(
                f"\n[{slot}/12] SKIP existing: "
                f"{scenario} / {app} / repetition {repetition}"
            )
            continue

        print("\n" + "=" * 72)
        print(
            f"[{slot}/12] {scenario} / {app} / repetition {repetition}/3"
        )
        for line in instructions(scenario, app):
            print(f"  - {line}")

        answer = input(
            "Press Enter to launch, or type q then Enter to pause: "
        ).strip().lower()
        if answer == "q":
            print("Comparison paused; successful results are preserved.")
            return 0

        rc = run_one(args, scenario, app)
        if rc != 0:
            return rc

        counts = successful_counts(args.results_dir)
        if counts[key] < repetition:
            print(
                "No successful EOS JSON was recorded for this run.",
                file=sys.stderr,
            )
            return 1

    print("\nAll 12 controlled comparison runs have successful EOS results.")
    rc = summarize(args.results_dir)
    if rc == 0:
        print(f"Summary: {args.results_dir / 'summary.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
