#!/usr/bin/env python3
"""Summarize repeated Troika benchmark JSON results."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.files
    ]
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
