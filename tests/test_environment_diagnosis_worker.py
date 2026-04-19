import sys
import tempfile
import types
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from src.utils.worker import EnvironmentDiagnosisWorker, WorkerResult


class _CaptureEnvironmentDiagnosisWorker(EnvironmentDiagnosisWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeHwp:
    def __init__(self, visible: bool = False) -> None:
        self.visible = visible
        self.quit_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1


class TestEnvironmentDiagnosisWorker(unittest.TestCase):
    def test_worker_reports_success(self) -> None:
        fake_pyhwpx = types.SimpleNamespace(__version__="0.0-test", Hwp=_FakeHwp)

        with tempfile.TemporaryDirectory() as td:
            with (
                patch.dict(sys.modules, {"pyhwpx": fake_pyhwpx}),
                patch("src.utils.worker.analysis.worker_com_context", return_value=nullcontext()),
            ):
                worker = _CaptureEnvironmentDiagnosisWorker(td)
                worker.run()

        assert worker.captured is not None
        self.assertTrue(worker.captured.success)
        data = worker.captured.data or {}
        self.assertEqual(data.get("fail_count"), 0)
        self.assertEqual(data.get("warn_count"), 0)
        self.assertIn("OK 4", str(data.get("summary")))

    def test_worker_reports_output_dir_write_failure(self) -> None:
        fake_pyhwpx = types.SimpleNamespace(__version__="0.0-test", Hwp=_FakeHwp)

        with tempfile.TemporaryDirectory() as td:
            with (
                patch.dict(sys.modules, {"pyhwpx": fake_pyhwpx}),
                patch("src.utils.worker.analysis.worker_com_context", return_value=nullcontext()),
                patch("src.utils.worker.analysis.Path.write_text", side_effect=OSError("disk full")),
            ):
                worker = _CaptureEnvironmentDiagnosisWorker(td)
                worker.run()

        assert worker.captured is not None
        self.assertFalse(worker.captured.success)
        data = worker.captured.data or {}
        self.assertEqual(data.get("fail_count"), 1)
        self.assertIn("FAIL 1", str(data.get("summary")))
