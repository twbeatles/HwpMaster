"""
Performance smoke checks for startup and hyperlink throughput.

Usage:
    python scripts/perf_smoke.py
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASELINE_IMPORT_PAGES_MS = 939.7
BASELINE_MAINWINDOW_INIT_MS = 485.6


def _run_python_snippet(code: str) -> float:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return float(proc.stdout.strip())


def measure_import_pages_ms() -> float:
    code = """
import importlib, time
t0 = time.perf_counter()
importlib.import_module("src.ui.pages")
print((time.perf_counter() - t0) * 1000.0)
""".strip()
    return _run_python_snippet(code)


def measure_mainwindow_init_ms() -> float:
    code = """
import time
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
app = QApplication([])
t0 = time.perf_counter()
w = MainWindow()
print((time.perf_counter() - t0) * 1000.0)
w.close()
app.quit()
""".strip()
    return _run_python_snippet(code)


def _throughput_ms(max_concurrency: int, cache_enabled: bool) -> tuple[float, int]:
    from src.core.hyperlink_checker import HyperlinkChecker, LinkCheckResult, LinkInfo, LinkStatus

    class SmokeChecker(HyperlinkChecker):
        def __init__(self) -> None:
            super().__init__(
                max_concurrency=max_concurrency,
                cache_enabled=cache_enabled,
                external_requests_enabled=True,
            )
            self.calls = 0

        def extract_links(self, source_path: str) -> LinkCheckResult:
            urls: list[str] = []
            for i in range(40):
                url = f"https://example{i % 10}.com/path/{i}"
                urls.extend([url] * 10)
            links = [LinkInfo(url=u, text=u, page=0) for u in urls]
            return LinkCheckResult(success=True, source_path=source_path, links=links)

        def check_url(self, url: str) -> tuple[LinkStatus, str]:
            self.calls += 1
            time.sleep(0.005)
            return LinkStatus.VALID, ""

    checker = SmokeChecker()
    t0 = time.perf_counter()
    checker.check_links("dummy.hwp")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return elapsed_ms, checker.calls


@dataclass
class PerfSummary:
    import_pages_ms: float
    mainwindow_init_ms: float
    import_pages_improvement_pct_vs_baseline: float
    mainwindow_improvement_pct_vs_baseline: float
    hyperlink_seq_no_cache_ms: float
    hyperlink_parallel_cache_ms: float
    hyperlink_calls_seq_no_cache: int
    hyperlink_calls_parallel_cache: int
    hyperlink_improvement_pct: float


def median(values: list[float]) -> float:
    return float(statistics.median(values))


def main() -> int:
    import_samples = [measure_import_pages_ms() for _ in range(5)]
    mainwindow_samples = [measure_mainwindow_init_ms() for _ in range(5)]

    import_pages_ms = median(import_samples)
    mainwindow_init_ms = median(mainwindow_samples)

    seq_ms, seq_calls = _throughput_ms(max_concurrency=1, cache_enabled=False)
    par_ms, par_calls = _throughput_ms(max_concurrency=8, cache_enabled=True)

    summary = PerfSummary(
        import_pages_ms=import_pages_ms,
        mainwindow_init_ms=mainwindow_init_ms,
        import_pages_improvement_pct_vs_baseline=((BASELINE_IMPORT_PAGES_MS - import_pages_ms) / BASELINE_IMPORT_PAGES_MS) * 100.0,
        mainwindow_improvement_pct_vs_baseline=((BASELINE_MAINWINDOW_INIT_MS - mainwindow_init_ms) / BASELINE_MAINWINDOW_INIT_MS) * 100.0,
        hyperlink_seq_no_cache_ms=seq_ms,
        hyperlink_parallel_cache_ms=par_ms,
        hyperlink_calls_seq_no_cache=seq_calls,
        hyperlink_calls_parallel_cache=par_calls,
        hyperlink_improvement_pct=((seq_ms - par_ms) / seq_ms) * 100.0 if seq_ms > 0 else 0.0,
    )

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
