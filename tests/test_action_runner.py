import tempfile
import unittest
from pathlib import Path

from src.core.action_runner import ActionRunner, ActionCommand


class _FakeHandler:
    def __init__(self) -> None:
        self.run_calls: list[str] = []
        self.execute_calls: list[tuple[str, str, dict]] = []

    def run_action(self, action_id: str) -> bool:
        self.run_calls.append(action_id)
        return action_id != "FAIL"

    def execute_action(self, action_id: str, pset_name: str, values: dict) -> bool:
        self.execute_calls.append((action_id, pset_name, values))
        return action_id != "FAIL_EXEC"


class TestActionRunner(unittest.TestCase):
    def test_run_commands_stop_on_error(self) -> None:
        runner = ActionRunner(template_dir=tempfile.mkdtemp())
        fake = _FakeHandler()
        commands = [
            ActionCommand(action_type="run", action_id="MoveDocBegin"),
            ActionCommand(action_type="run", action_id="FAIL"),
            ActionCommand(action_type="run", action_id="MoveDocEnd"),
        ]

        result = runner.run_commands(commands, stop_on_error=True, handler=fake)

        self.assertFalse(result.success)
        self.assertEqual(fake.run_calls, ["MoveDocBegin", "FAIL"])
        self.assertEqual(len(result.artifacts.get("failed_commands", [])), 1)

    def test_run_commands_continue_on_error(self) -> None:
        runner = ActionRunner(template_dir=tempfile.mkdtemp())
        fake = _FakeHandler()
        commands = [
            ActionCommand(action_type="run", action_id="FAIL"),
            ActionCommand(action_type="execute", action_id="InsertText", pset_name="HInsertText", values={"Text": "A"}),
        ]

        result = runner.run_commands(commands, stop_on_error=False, handler=fake)

        self.assertFalse(result.success)
        self.assertEqual(fake.run_calls, ["FAIL"])
        self.assertEqual(len(fake.execute_calls), 1)
        self.assertGreaterEqual(result.changed_count, 1)

    def test_template_save_load_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runner = ActionRunner(template_dir=td)
            commands = [
                ActionCommand(action_type="run", action_id="MoveDocBegin"),
                ActionCommand(action_type="execute", action_id="InsertText", pset_name="HInsertText", values={"Text": "hello"}),
            ]

            self.assertTrue(runner.save_template("sample", commands, "desc"))
            self.assertIsNotNone(runner.get_template("sample"))

            runner2 = ActionRunner(template_dir=td)
            tpl = runner2.get_template("sample")
            self.assertIsNotNone(tpl)
            assert tpl is not None
            self.assertEqual(len(tpl.commands), 2)

            self.assertTrue(runner2.delete_template("sample"))
            self.assertIsNone(runner2.get_template("sample"))

    def test_builtin_execute_presets_exist(self) -> None:
        runner = ActionRunner(template_dir=tempfile.mkdtemp())
        presets = runner.list_builtin_presets()

        self.assertGreaterEqual(len(presets), 4)
        ids = {p.preset_id for p in presets}
        self.assertIn("table_professional_style", ids)
        self.assertIn("image_print_enhance", ids)
        self.assertTrue(all(cmd.action_type == "execute" for p in presets for cmd in p.commands))

    def test_build_builtin_preset_commands_with_overrides(self) -> None:
        runner = ActionRunner(template_dir=tempfile.mkdtemp())
        commands = runner.build_builtin_preset_commands(
            "image_print_enhance",
            value_overrides={
                "#0": {"Brightness": 99},
                "ShapeObjDialog": {"Transparency": 33},
            },
        )

        self.assertEqual(commands[0].values.get("Brightness"), 99)
        self.assertEqual(commands[1].values.get("Transparency"), 33)

    def test_run_builtin_preset_executes_commands(self) -> None:
        runner = ActionRunner(template_dir=tempfile.mkdtemp())
        fake = _FakeHandler()

        result = runner.run_builtin_preset("table_dense_grid", handler=fake)

        self.assertTrue(result.success)
        self.assertEqual(len(fake.execute_calls), 1)
        self.assertEqual(fake.execute_calls[0][0], "CellBorder")

    def test_run_builtin_preset_invalid_id_returns_error(self) -> None:
        runner = ActionRunner(template_dir=tempfile.mkdtemp())
        result = runner.run_builtin_preset("not_exists")
        self.assertFalse(result.success)
        self.assertIn("프리셋", str(result.error))


if __name__ == "__main__":
    unittest.main()
