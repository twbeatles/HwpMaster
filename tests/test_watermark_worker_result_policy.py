import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from src.utils.worker import WatermarkWorker, WorkerResult


class _CaptureWatermarkWorker(WatermarkWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeWatermarkManager:
    @classmethod
    def _mixed_results(cls):
        return [
            SimpleNamespace(success=True, source_path=r"C:\in\ok.hwp", error_message=None),
            SimpleNamespace(success=False, source_path=r"C:\in\bad.hwp", error_message="watermark failed"),
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def batch_apply_watermark(self, source_files, config, output_dir, progress_callback=None):
        return self._mixed_results()

    def remove_watermark(self, source_path, output_path=None):
        return SimpleNamespace(success=True, source_path=source_path, error_message=None)


class TestWatermarkWorkerResultPolicy(unittest.TestCase):
    def test_partial_failure_sets_worker_result_to_failure(self) -> None:
        with (
            patch("src.utils.worker.com_context", return_value=nullcontext()),
            patch("src.core.watermark_manager.WatermarkManager", _FakeWatermarkManager),
        ):
            worker = _CaptureWatermarkWorker(
                mode="apply",
                files=[r"C:\in\ok.hwp", r"C:\in\bad.hwp"],
                config=object(),
                output_dir=r"C:\out",
            )
            worker.run()

        assert worker.captured is not None
        self.assertFalse(worker.captured.success)
        self.assertEqual((worker.captured.data or {}).get("success_count"), 1)
        self.assertEqual((worker.captured.data or {}).get("fail_count"), 1)
        self.assertIn("bad.hwp", str(worker.captured.error_message))
        self.assertIn("watermark failed", str(worker.captured.error_message))


if __name__ == "__main__":
    unittest.main()

