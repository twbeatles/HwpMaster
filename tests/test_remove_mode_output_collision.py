import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.utils.worker import HeaderFooterWorker, WatermarkWorker, WorkerResult


class _CaptureHeaderFooterWorker(HeaderFooterWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _CaptureWatermarkWorker(WatermarkWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeHeaderFooterManager:
    saved_paths: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def batch_apply_header_footer(self, source_files, config, output_dir, progress_callback=None):
        return []

    def remove_header_footer(self, source_path, output_path=None):
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ok", encoding="utf-8")
            self.__class__.saved_paths.append(str(path))
        return SimpleNamespace(success=True, source_path=source_path, error_message=None)


class _FakeWatermarkManager:
    saved_paths: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def batch_apply_watermark(self, source_files, config, output_dir, progress_callback=None):
        return []

    def remove_watermark(self, source_path, output_path=None):
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ok", encoding="utf-8")
            self.__class__.saved_paths.append(str(path))
        return SimpleNamespace(success=True, source_path=source_path, error_message=None)


class TestRemoveModeOutputCollision(unittest.TestCase):
    def setUp(self) -> None:
        _FakeHeaderFooterManager.saved_paths = []
        _FakeWatermarkManager.saved_paths = []

    def test_header_footer_remove_uses_collision_free_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            files = [
                str(Path(td) / "a" / "doc.hwp"),
                str(Path(td) / "b" / "doc.hwp"),
            ]
            out_dir = str(Path(td) / "hf_out")

            with (
                patch("src.utils.worker.com_context", return_value=nullcontext()),
                patch("src.core.header_footer_manager.HeaderFooterManager", _FakeHeaderFooterManager),
            ):
                worker = _CaptureHeaderFooterWorker("remove", files, output_dir=out_dir)
                worker.run()

            assert worker.captured is not None
            self.assertTrue(worker.captured.success)
            self.assertEqual(len(_FakeHeaderFooterManager.saved_paths), 2)
            self.assertNotEqual(_FakeHeaderFooterManager.saved_paths[0], _FakeHeaderFooterManager.saved_paths[1])
            self.assertEqual(Path(_FakeHeaderFooterManager.saved_paths[0]).name, "doc.hwp")
            self.assertEqual(Path(_FakeHeaderFooterManager.saved_paths[1]).name, "doc_1.hwp")

    def test_watermark_remove_uses_collision_free_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            files = [
                str(Path(td) / "a" / "doc.hwp"),
                str(Path(td) / "b" / "doc.hwp"),
            ]
            out_dir = str(Path(td) / "wm_out")

            with (
                patch("src.utils.worker.com_context", return_value=nullcontext()),
                patch("src.core.watermark_manager.WatermarkManager", _FakeWatermarkManager),
            ):
                worker = _CaptureWatermarkWorker("remove", files, output_dir=out_dir)
                worker.run()

            assert worker.captured is not None
            self.assertTrue(worker.captured.success)
            self.assertEqual(len(_FakeWatermarkManager.saved_paths), 2)
            self.assertNotEqual(_FakeWatermarkManager.saved_paths[0], _FakeWatermarkManager.saved_paths[1])
            self.assertEqual(Path(_FakeWatermarkManager.saved_paths[0]).name, "doc.hwp")
            self.assertEqual(Path(_FakeWatermarkManager.saved_paths[1]).name, "doc_1.hwp")


if __name__ == "__main__":
    unittest.main()

