import unittest
from contextlib import nullcontext
from unittest.mock import patch

from src.core.bookmark_manager import BookmarkResult
from src.utils.worker import BookmarkWorker, WorkerResult


class _CaptureBookmarkWorker(BookmarkWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeBookmarkManagerPartialFail:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def batch_delete_bookmarks(self, files, output_dir, progress_callback=None):
        return [
            BookmarkResult(success=True, source_path=str(files[0])),
            BookmarkResult(success=False, source_path=str(files[1]), error_message="delete failed"),
        ]


class _FakeBookmarkManagerDeleteSelected:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def batch_delete_selected_bookmarks(self, selected_map, output_dir, progress_callback=None):
        return [
            BookmarkResult(success=True, source_path=path)
            for path in selected_map.keys()
        ]


class TestBookmarkWorkerPolicy(unittest.TestCase):
    def test_partial_failure_marks_worker_failure_and_summarizes_errors(self) -> None:
        files = ["a.hwp", "b.hwp"]
        with (
            patch("src.utils.worker.com_context", return_value=nullcontext()),
            patch("src.core.bookmark_manager.BookmarkManager", _FakeBookmarkManagerPartialFail),
        ):
            worker = _CaptureBookmarkWorker(mode="delete", files=files, output_dir="out")
            worker.run()

        assert worker.captured is not None
        self.assertFalse(worker.captured.success)
        self.assertEqual(worker.captured.data.get("success_count"), 1)
        self.assertEqual(worker.captured.data.get("fail_count"), 1)
        self.assertIn("b.hwp", str(worker.captured.error_message))
        self.assertIn("delete failed", str(worker.captured.error_message))

    def test_delete_selected_success_uses_fail_count_policy(self) -> None:
        selected_map = {
            "a.hwp": ["BM1", "BM2"],
            "b.hwp": ["BM3"],
        }
        with (
            patch("src.utils.worker.com_context", return_value=nullcontext()),
            patch("src.core.bookmark_manager.BookmarkManager", _FakeBookmarkManagerDeleteSelected),
        ):
            worker = _CaptureBookmarkWorker(
                mode="delete_selected",
                files=[],
                output_dir="out",
                selected_map=selected_map,
            )
            worker.run()

        assert worker.captured is not None
        self.assertTrue(worker.captured.success)
        self.assertEqual(worker.captured.data.get("success_count"), 2)
        self.assertEqual(worker.captured.data.get("fail_count"), 0)
        self.assertEqual(worker.captured.data.get("total"), 2)


if __name__ == "__main__":
    unittest.main()
