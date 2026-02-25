import py_compile
import tempfile
import unittest
from pathlib import Path

from src.core.macro_recorder import MacroRecorder, MacroAction


class TestMacroRecorderPresets(unittest.TestCase):
    def test_quote_preset_replacements_are_valid_pairs(self) -> None:
        presets = MacroRecorder.get_preset_macros()
        quote_preset = next(p for p in presets if p["name"] == "따옴표 통일")
        replacements = quote_preset["replacements"]

        self.assertTrue(replacements)
        for item in replacements:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], str)
            self.assertIsInstance(item[1], str)

        self.assertIn(("“", '"'), replacements)
        self.assertIn(("”", '"'), replacements)
        self.assertIn(("‘", "'"), replacements)
        self.assertIn(("’", "'"), replacements)

    def test_exported_macro_script_is_compilable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            recorder = MacroRecorder(base_dir=td)
            macro = recorder.create_batch_replace_macro(
                name="compile-check",
                replacements=[("foo", "bar"), ("baz", "qux")],
            )
            script_path = Path(td) / "macro_export.py"
            ok = recorder.export_macro(macro.id, str(script_path))

            self.assertTrue(ok)
            self.assertTrue(script_path.exists())
            py_compile.compile(str(script_path), doraise=True)

    def test_to_python_code_uses_supported_patterns(self) -> None:
        action = MacroAction(action_type="set_size", params={"size": 11})
        code = action.to_python_code()
        self.assertIn("PointToHwpUnit", code)
        self.assertNotIn("set_font_size", code)

        action2 = MacroAction(action_type="set_color", params={"color": "#ff0000"})
        code2 = action2.to_python_code()
        self.assertIn("RGBColor", code2)
        self.assertNotIn("set_text_color", code2)


if __name__ == "__main__":
    unittest.main()

