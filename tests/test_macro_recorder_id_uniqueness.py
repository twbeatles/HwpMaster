import tempfile
import unittest
import uuid
from datetime import datetime as _RealDatetime
from unittest.mock import patch

from src.core.macro_recorder import MacroAction, MacroRecorder


class _FixedDatetime:
    @classmethod
    def now(cls):
        return _RealDatetime(2026, 3, 3, 12, 0, 0, 123456)


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

    def test_save_macro_avoids_id_collision_when_timestamp_is_same(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            recorder = MacroRecorder(base_dir=td)
            actions = [MacroAction(action_type="run_action", params={"action_id": "MoveDocBegin"})]

            with (
                patch("src.core.macro_recorder.datetime", _FixedDatetime),
                patch(
                    "uuid.uuid4",
                    side_effect=[
                        uuid.UUID("11111111-1111-1111-1111-111111111111"),
                        uuid.UUID("22222222-2222-2222-2222-222222222222"),
                    ],
                ),
            ):
                macro1 = recorder.save_macro("macro1", actions)
                macro2 = recorder.save_macro("macro2", actions)

            self.assertNotEqual(macro1.id, macro2.id)
            self.assertTrue((recorder._base_dir / f"{macro1.id}.py").exists())
            self.assertTrue((recorder._base_dir / f"{macro2.id}.py").exists())


if __name__ == "__main__":
    unittest.main()
