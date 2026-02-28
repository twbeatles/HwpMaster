import unittest
from contextlib import nullcontext
from unittest.mock import patch

from src.core.hyperlink_checker import LinkCheckResult, LinkInfo, LinkStatus
from src.utils.worker import HyperlinkWorker, WorkerResult


class _CaptureHyperlinkWorker(HyperlinkWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeHyperlinkChecker:
    def __init__(self, *args, **kwargs) -> None:
        return

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def check_links(self, source_path: str) -> LinkCheckResult:
        return LinkCheckResult(
            success=True,
            source_path=source_path,
            links=[LinkInfo(url="https://example.com", text="example", page=1, status=LinkStatus.VALID)],
            valid_count=1,
            broken_count=0,
        )

    def generate_report(self, result: LinkCheckResult, output_path: str) -> bool:
        return False


class TestHyperlinkWorkerReportSavePolicy(unittest.TestCase):
    def test_report_save_failure_counts_as_failure(self) -> None:
        with (
            patch("src.utils.worker.com_context", return_value=nullcontext()),
            patch("src.core.hyperlink_checker.HyperlinkChecker", _FakeHyperlinkChecker),
        ):
            worker = _CaptureHyperlinkWorker(
                files=["a.hwp"],
                output_dir="out",
            )
            worker.run()

        assert worker.captured is not None
        self.assertFalse(worker.captured.success)
        data = worker.captured.data or {}
        self.assertEqual(data.get("success_count"), 0)
        self.assertEqual(data.get("fail_count"), 1)
        self.assertEqual(data.get("report_fail_count"), 1)
        self.assertTrue(data.get("warnings"))


if __name__ == "__main__":
    unittest.main()
