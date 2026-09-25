#!/usr/bin/env python3
"""Summarize repeated Troika benchmark JSON results."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


METRICS = (
    ("startup_proxy_ms", "startup ms"),
    ("idle.cpu_mean_pct", "idle CPU %"),
    ("idle.rss_mean_mib", "idle RSS MiB"),
    ("recording.cpu_mean_pct", "record CPU %"),
    ("recording.rss_mean_mib", "record RSS MiB"),
    ("recording.rss_peak_mib", "record RSS peak MiB"),
    ("finalization_ms", "finalize ms"),
)


def nested_value(payload: dict, dotted: str):
    value = payload
    for part in dotted.split("."):
        value = value[part]
    return value


def median(values: list[float]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(statistics.median(clean), 3) if clean else None


def validate_lite_matrix(payloads: list[dict]) -> set[tuple[int, bool, bool]]:
    expected = {
        (fps, mic, system_audio)
        for fps in (15, 30)
        for mic in (False, True)
        for system_audio in (False, True)
    }
    observed = {
        (
            int(payload["fps"]),
            bool(payload["microphone"]),
            bool(payload["system_audio"]),
        )
        for payload in payloads
        if payload.get("app") == "lite"
    }
    return expected - observed


def validate_controlled_comparison(
    payloads: list[dict],
    repetitions: int = 3,
) -> dict[tuple[str, str], int]:
    expected = {
        ("A-15-video-low", "lite"): repetitions,
        ("A-15-video-low", "troika-d"): repetitions,
        ("B-30-dual-high", "lite"): repetitions,
        ("B-30-dual-high", "troika-d"): repetitions,
    }
    observed = Counter(
        (payload.get("scenario"), payload.get("app"))
        for payload in payloads
        if payload.get("finalization_outcome") == "eos"
    )
    return {
        key: required - observed.get(key, 0)
        for key, required in expected.items()
        if observed.get(key, 0) < required
    }


def aggregate(payloads: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for payload in payloads:
        groups[(payload["scenario"], payload["app"])].append(payload)

    rows = []
    for (scenario, app), items in sorted(groups.items()):
        row = {
            "scenario": scenario,
            "app": app,
            "runs": len(items),
        }
        for dotted, label in METRICS:
            row[label] = median(
                [nested_value(item, dotted) for item in items]
            )
        row["finalization outcomes"] = ",".join(
            sorted(
                {
                    str(item.get("finalization_outcome"))
                    for item in items
                }
            )
        )
        rows.append(row)
    return rows


def markdown_table(rows: list[dict]) -> str:
    headers = [
        "scenario",
        "app",
        "runs",
        *[label for _dotted, label in METRICS],
        "finalization outcomes",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        cells = []
        for header in headers:
            value = row.get(header)
            cells.append("" if value is None else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--require-lite-matrix",
        action="store_true",
        help="Fail unless all 8 Lite FPS/audio combinations are present.",
    )
    parser.add_argument(
        "--require-controlled-comparison",
        action="store_true",
        help="Fail unless A/B each have 3 EOS runs per application.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.files
    ]
    if args.require_lite_matrix:
        missing = validate_lite_matrix(payloads)
        if missing:
            formatted = ", ".join(
                f"fps={fps},mic={int(mic)},system={int(system)}"
                for fps, mic, system in sorted(missing)
            )
            raise SystemExit(f"Incomplete Lite performance matrix: {formatted}")
        print("Lite 8-case performance matrix: COMPLETE")

    if args.require_controlled_comparison:
        missing = validate_controlled_comparison(payloads)
        if missing:
            formatted = ", ".join(
                f"{scenario}/{app}:missing={count}"
                for (scenario, app), count in sorted(missing.items())
            )
            raise SystemExit(
                f"Incomplete controlled comparison: {formatted}"
            )
        print("Controlled comparison repetitions: COMPLETE")

    rows = aggregate(payloads)
    print(markdown_table(rows))
    if args.json_out:
        args.json_out.write_text(
            json.dumps(rows, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
