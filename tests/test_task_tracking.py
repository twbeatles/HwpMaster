import tempfile
import unittest
from pathlib import Path

from src.utils.history_manager import TaskType, get_history_manager
from src.utils.settings import SettingsManager
from src.utils.task_tracking import record_task_summary, track_recent_files


class TestTaskTracking(unittest.TestCase):
    def test_track_recent_files_deduplicates_and_preserves_latest_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            settings = SettingsManager(config_dir=td)
            first = Path(td) / "a.hwp"
            second = Path(td) / "b.hwpx"
            first.write_text("a", encoding="utf-8")
            second.write_text("b", encoding="utf-8")

            track_recent_files([str(first), str(second), str(first)], settings=settings)

            self.assertEqual(settings.get_recent_files(), [str(first), str(second)])

    def test_record_task_summary_writes_history_in_same_config_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            settings = SettingsManager(config_dir=td)
            target = Path(td) / "result.hwp"
            target.write_text("ok", encoding="utf-8")

            record_task_summary(
                TaskType.TEMPLATE,
                "템플릿 생성",
                [str(target)],
                success_count=1,
                fail_count=0,
                settings=settings,
                history_manager=get_history_manager(config_dir=td),
            )

            history = get_history_manager(config_dir=td).get_recent(1)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].task_type, TaskType.TEMPLATE.value)
            self.assertEqual(settings.get_recent_files(), [str(target)])
