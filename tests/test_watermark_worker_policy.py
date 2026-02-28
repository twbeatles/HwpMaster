import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from src.utils.worker import WatermarkWorker, WorkerResult


class _CaptureWatermarkWorker(WatermarkWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeResult:
    def __init__(self, success: bool, source_path: str, error_message: str = "") -> None:
        self.success = success
        self.source_path = source_path
        self.error_message = error_message


class _FakeWatermarkManagerPartialFail:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def batch_apply_watermark(self, files, config, output_dir, progress_callback=None):
        return [
            _FakeResult(True, str(files[0])),
            _FakeResult(False, str(files[1]), "apply failed"),
        ]


class _FakeWatermarkManagerRemove:
    saved_paths: list[str] = []

    def __enter__(self):
        self.__class__.saved_paths = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def remove_watermark(self, source_path: str, output_path: str):
        if output_path:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
            self.__class__.saved_paths.append(str(target))
        return _FakeResult(True, source_path)


class TestWatermarkWorkerPolicy(unittest.TestCase):
    def test_partial_failure_sets_worker_failure(self) -> None:
        files = ["a.hwp", "b.hwp"]
        with (
            patch("src.utils.worker.com_context", return_value=nullcontext()),
            patch("src.core.watermark_manager.WatermarkManager", _FakeWatermarkManagerPartialFail),
        ):
            worker = _CaptureWatermarkWorker(
                mode="apply",
                files=files,
                config=object(),
                output_dir="out",
            )
            worker.run()

        assert worker.captured is not None
        self.assertFalse(worker.captured.success)
        data = worker.captured.data or {}
        self.assertEqual(data.get("success_count"), 1)
        self.assertEqual(data.get("fail_count"), 1)
        self.assertIn("apply failed", worker.captured.error_message or "")

    def test_remove_mode_avoids_output_name_collision(self) -> None:
        files = ["C:/a/report.hwp", "D:/b/report.hwp"]
        with tempfile.TemporaryDirectory() as td:
            out_dir = str(Path(td) / "out")
            with (
                patch("src.utils.worker.com_context", return_value=nullcontext()),
                patch("src.core.watermark_manager.WatermarkManager", _FakeWatermarkManagerRemove),
            ):
                worker = _CaptureWatermarkWorker(
                    mode="remove",
                    files=files,
                    output_dir=out_dir,
                )
                worker.run()

            paths = _FakeWatermarkManagerRemove.saved_paths
            self.assertEqual(len(paths), 2)
            self.assertNotEqual(paths[0], paths[1])
            self.assertTrue(paths[0].endswith("report.hwp"))
            self.assertTrue(paths[1].endswith("report_1.hwp"))


if __name__ == "__main__":
    unittest.main()
