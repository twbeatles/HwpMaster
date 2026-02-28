import tempfile
import unittest

from src.core.macro_recorder import MacroAction, MacroRecorder


class TestMacroRecorderIdUniqueness(unittest.TestCase):
    def test_save_macro_generates_unique_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            recorder = MacroRecorder(base_dir=td)

            first = recorder.save_macro(
                name="first",
                actions=[MacroAction(action_type="run_action", params={"action_id": "MoveDocBegin"})],
            )
            second = recorder.save_macro(
                name="second",
                actions=[MacroAction(action_type="run_action", params={"action_id": "MoveDocEnd"})],
            )

            self.assertNotEqual(first.id, second.id)

            macros = recorder.get_all_macros()
            self.assertEqual(len(macros), 2)
            self.assertEqual({m.name for m in macros}, {"first", "second"})


if __name__ == "__main__":
    unittest.main()
