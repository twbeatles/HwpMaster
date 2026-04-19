import json
import tempfile
import unittest
from pathlib import Path

from src.utils.history_manager import HistoryItem, TaskType, get_history_manager
from src.utils.settings import SettingsManager
from src.utils.task_tracking import record_task_result
from src.utils.worker import WorkerResult


class TestHistoryStatus(unittest.TestCase):
    def test_history_item_infers_legacy_status(self) -> None:
        item = HistoryItem(
            id="1",
            task_type=TaskType.TEMPLATE.value,
            description="legacy",
            file_count=2,
            success_count=1,
            fail_count=1,
            timestamp="2026-04-19T00:00:00",
        )
        self.assertEqual(item.status, "partial")

    def test_history_manager_loads_legacy_json_without_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_file = Path(td) / "history.json"
            history_file.write_text(
                json.dumps(
                    [
                        {
                            "id": "1",
                            "task_type": TaskType.MERGE.value,
                            "description": "merge",
                            "file_count": 2,
                            "success_count": 0,
                            "fail_count": 1,
                            "timestamp": "2026-04-19T00:00:00",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manager = get_history_manager(config_dir=td)
            recent = manager.get_recent(1)
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0].status, "failed")

    def test_record_task_result_persists_cancelled_without_recent_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            settings = SettingsManager(config_dir=td)
            history = get_history_manager(config_dir=td)
            history.clear()

            target = Path(td) / "target.hwp"
            target.write_text("doc", encoding="utf-8")

            item = record_task_result(
                TaskType.DATA_INJECT,
                "데이터 주입",
                [str(target)],
                WorkerResult(
                    success=False,
                    data={
                        "cancelled": True,
                        "success_count": 0,
                        "fail_count": 0,
                    },
                    error_message="취소",
                ),
                settings=settings,
                history_manager=history,
            )

            self.assertIsNotNone(item)
            assert item is not None
            self.assertEqual(item.status, "cancelled")
            self.assertEqual(settings.get_recent_files(), [])
            self.assertEqual(history.get_recent(1)[0].status, "cancelled")
