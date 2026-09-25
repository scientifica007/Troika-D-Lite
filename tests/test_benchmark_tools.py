import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


benchmark = load(
    "benchmark_session",
    ROOT / "scripts" / "benchmark_session.py",
)
summary = load(
    "summarize_benchmarks",
    ROOT / "scripts" / "summarize_benchmarks.py",
)


class BenchmarkMathTests(unittest.TestCase):
    def test_cpu_percent_uses_interval_delta(self):
        a = benchmark.ProcSample(at=10.0, cpu_ticks=100, rss_kib=1000)
        b = benchmark.ProcSample(
            at=11.0,
            cpu_ticks=100 + benchmark.CLK_TCK,
            rss_kib=2000,
        )
        self.assertAlmostEqual(benchmark.cpu_percent(a, b), 100.0)

    def test_sample_summary_uses_mib_and_peak(self):
        samples = [
            benchmark.ProcSample(1.0, 0, 1024),
            benchmark.ProcSample(
                2.0,
                benchmark.CLK_TCK // 2,
                2048,
            ),
        ]
        result = benchmark.summarize_samples(samples)
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["rss_mean_mib"], 1.5)
        self.assertEqual(result["rss_peak_mib"], 2.0)


class BenchmarkSummaryTests(unittest.TestCase):
    def test_aggregate_uses_median_per_app_and_scenario(self):
        payloads = []
        for startup in (100, 200, 300):
            payloads.append(
                {
                    "scenario": "s1",
                    "app": "lite",
                    "startup_proxy_ms": startup,
                    "idle": {
                        "cpu_mean_pct": 1,
                        "rss_mean_mib": 10,
                    },
                    "recording": {
                        "cpu_mean_pct": 20,
                        "rss_mean_mib": 30,
                        "rss_peak_mib": 40,
                    },
                    "finalization_ms": 500,
                    "finalization_outcome": "eos",
                }
            )
        rows = summary.aggregate(payloads)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["runs"], 3)
        self.assertEqual(rows[0]["startup ms"], 200.0)


if __name__ == "__main__":
    unittest.main()
