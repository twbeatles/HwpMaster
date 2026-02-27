import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from src.core.hwp_handler import OperationResult
from src.utils.worker import ActionConsoleWorker, WorkerResult


class _CaptureActionConsoleWorker(ActionConsoleWorker):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.captured: WorkerResult | None = None

    def _emit_finished_once(self, result: WorkerResult) -> None:
        self.captured = result


class _FakeHwpDocument:
    def __init__(self) -> None:
        self.open_calls: list[str] = []
        self.save_calls: list[str] = []

    def open(self, path: str) -> None:
        self.open_calls.append(path)

    def save_as(self, path: str) -> None:
        self.save_calls.append(path)


class _FakeHwpHandler:
    last_instance = None

    def __init__(self) -> None:
        self._doc = _FakeHwpDocument()
        _FakeHwpHandler.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def _get_hwp(self) -> _FakeHwpDocument:
        return self._doc


class _FakeActionRunner:
    def run_commands(self, commands, stop_on_error=True, handler=None):
        return OperationResult(
            success=True,
            warnings=[],
            changed_count=len(commands),
            artifacts={
                "executed": [c.__dict__ for c in commands],
                "succeeded_commands": [c.__dict__ for c in commands],
                "failed_commands": [],
            },
            error=None,
        )


class _FakeRecorder:
    @property
    def is_recording(self) -> bool:
        return False

    def record_action(self, *args, **kwargs) -> None:
        return


class TestActionConsoleWorkerSavePolicy(unittest.TestCase):
    def test_save_mode_none_sets_artifact_and_skips_save(self) -> None:
        commands = [{"action_type": "run", "action_id": "MoveDocBegin"}]
        with (
            patch("src.utils.worker.com_context", return_value=nullcontext()),
            patch("src.core.hwp_handler.HwpHandler", _FakeHwpHandler),
            patch("src.core.action_runner.ActionRunner", _FakeActionRunner),
            patch("src.core.macro_recorder.MacroRecorder", _FakeRecorder),
        ):
            worker = _CaptureActionConsoleWorker(
                source_file="",
                commands=commands,
                save_mode="none",
            )
            worker.run()

        assert worker.captured is not None
        self.assertTrue(worker.captured.success)
        artifacts = (worker.captured.data or {}).get("artifacts", {})
        self.assertFalse(artifacts.get("saved"))
        self.assertEqual(artifacts.get("save_mode"), "none")

    def test_save_mode_new_saves_to_output_path(self) -> None:
        commands = [{"action_type": "run", "action_id": "MoveDocBegin"}]
        with tempfile.TemporaryDirectory() as td:
            source = str(Path(td) / "source.hwp")
            output = str(Path(td) / "edited.hwp")

            with (
                patch("src.utils.worker.com_context", return_value=nullcontext()),
                patch("src.core.hwp_handler.HwpHandler", _FakeHwpHandler),
                patch("src.core.action_runner.ActionRunner", _FakeActionRunner),
                patch("src.core.macro_recorder.MacroRecorder", _FakeRecorder),
            ):
                worker = _CaptureActionConsoleWorker(
                    source_file=source,
                    commands=commands,
                    save_mode="new",
                    output_path=output,
                )
                worker.run()

        assert worker.captured is not None
        self.assertTrue(worker.captured.success)
        artifacts = (worker.captured.data or {}).get("artifacts", {})
        self.assertTrue(artifacts.get("saved"))
        self.assertEqual(artifacts.get("saved_path"), output)
        self.assertEqual(artifacts.get("save_mode"), "new")

        instance = _FakeHwpHandler.last_instance
        self.assertIsNotNone(instance)
        assert instance is not None
        self.assertEqual(instance._doc.open_calls, [source])
        self.assertEqual(instance._doc.save_calls, [output])


if __name__ == "__main__":
    unittest.main()
