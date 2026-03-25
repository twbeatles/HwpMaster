import tempfile
import unittest
from pathlib import Path

from src.core.action_runner import ActionCommand, ActionRunner
from src.core.macro_recorder import MacroAction, MacroRecorder
from src.core.template_store import TemplateStore
from src.utils.atomic_write import atomic_write_json, atomic_write_text
from src.utils.history_manager import HistoryManager, TaskType
from src.utils.settings import SettingsManager


class TestAtomicStorage(unittest.TestCase):
    def test_atomic_write_text_preserves_original_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target_dir = Path(td)
            target = target_dir / "sample.txt"
            target.write_text("before", encoding="utf-8")

            from unittest.mock import patch

            with patch("src.utils.atomic_write._replace_path", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    atomic_write_text(target, "after")

            self.assertEqual(target.read_text(encoding="utf-8"), "before")
            self.assertEqual(list(target_dir.glob("*.tmp")), [])

    def test_atomic_write_json_updates_target_and_leaves_no_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "payload.json"
            atomic_write_json(target, {"name": "테스트"}, ensure_ascii=False)

            self.assertTrue(target.exists())
            self.assertIn("테스트", target.read_text(encoding="utf-8"))
            self.assertEqual(list(Path(td).glob("*.tmp")), [])

    def test_settings_history_action_macro_template_saves_leave_no_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            settings = SettingsManager(config_dir=td)
            settings.set("theme_preset", "Light")

            history = HistoryManager(config_dir=td)
            history.add(TaskType.CONVERT, "PDF 변환", ["a.hwp"], 1, 0)

            action_dir = Path(td) / "actions"
            runner = ActionRunner(template_dir=str(action_dir))
            runner.save_template(
                "sample",
                [ActionCommand(action_type="run", action_id="MoveDocBegin")],
                "desc",
            )

            macro_dir = Path(td) / "macros"
            recorder = MacroRecorder(base_dir=str(macro_dir))
            macro = recorder.save_macro(
                "macro",
                [MacroAction(action_type="run_action", params={"action_id": "MoveDocBegin"})],
            )

            template_dir = Path(td) / "templates"
            source = Path(td) / "sample.hwp"
            source.write_text("template", encoding="utf-8")
            store = TemplateStore(base_dir=str(template_dir))
            store.add_user_template("sample", str(source))

            self.assertTrue((Path(td) / "settings.json").exists())
            self.assertTrue((Path(td) / "history.json").exists())
            self.assertTrue((action_dir / "action_templates.json").exists())
            self.assertTrue((macro_dir / f"{macro.id}.py").exists())
            self.assertTrue((template_dir / "templates.json").exists())
            self.assertEqual(list(Path(td).rglob("*.tmp")), [])
