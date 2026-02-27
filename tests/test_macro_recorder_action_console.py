import tempfile
import unittest

from src.core.macro_recorder import MacroAction, MacroRecorder


class _FakePSet:
    def __init__(self) -> None:
        self.HSet = object()
        self.Text = ""


class _FakeHAction:
    def __init__(self) -> None:
        self.get_default_calls: list[tuple[str, object]] = []
        self.execute_calls: list[tuple[str, object]] = []

    def GetDefault(self, action_id: str, hset: object) -> None:
        self.get_default_calls.append((action_id, hset))

    def Execute(self, action_id: str, hset: object) -> None:
        self.execute_calls.append((action_id, hset))


class _FakeHwp:
    def __init__(self) -> None:
        self.run_calls: list[str] = []
        self.HAction = _FakeHAction()
        self.HParameterSet = type("FakeParamSet", (), {"HInsertText": _FakePSet()})()

    def Run(self, action_id: str) -> None:
        self.run_calls.append(action_id)


class TestMacroRecorderActionConsole(unittest.TestCase):
    def setUp(self) -> None:
        MacroRecorder._global_recording = False
        MacroRecorder._global_actions = []

    def tearDown(self) -> None:
        MacroRecorder._global_recording = False
        MacroRecorder._global_actions = []

    def test_recording_session_is_shared_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            recorder_a = MacroRecorder(base_dir=td)
            recorder_b = MacroRecorder(base_dir=td)

            recorder_a.start_recording()
            recorder_b.record_action("run_action", {"action_id": "MoveDocEnd"}, "문서 끝 이동")
            actions = recorder_a.stop_recording()

            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0].action_type, "run_action")
            self.assertEqual(actions[0].params.get("action_id"), "MoveDocEnd")

    def test_execute_action_supports_run_action_and_execute_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            recorder = MacroRecorder(base_dir=td)
            fake = _FakeHwp()

            recorder._execute_action(
                fake,
                MacroAction(action_type="run_action", params={"action_id": "MoveDocBegin"}),
            )
            recorder._execute_action(
                fake,
                MacroAction(
                    action_type="execute_action",
                    params={
                        "action_id": "InsertText",
                        "pset_name": "HInsertText",
                        "values": {"Text": "hello", "UnknownKey": "ignored"},
                    },
                ),
            )

            self.assertEqual(fake.run_calls, ["MoveDocBegin"])
            self.assertEqual(len(fake.HAction.get_default_calls), 1)
            self.assertEqual(len(fake.HAction.execute_calls), 1)
            self.assertEqual(fake.HAction.get_default_calls[0][0], "InsertText")
            self.assertEqual(fake.HAction.execute_calls[0][0], "InsertText")
            self.assertEqual(fake.HParameterSet.HInsertText.Text, "hello")
            self.assertFalse(hasattr(fake.HParameterSet.HInsertText, "UnknownKey"))


if __name__ == "__main__":
    unittest.main()
