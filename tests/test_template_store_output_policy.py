import tempfile
import unittest
from pathlib import Path

from src.core.template_store import TemplateStore


class TestTemplateStoreOutputPolicy(unittest.TestCase):
    def test_use_template_rejects_mismatched_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample.hwpx"
            source.write_text("template", encoding="utf-8")
            store = TemplateStore(base_dir=td)
            template = store.add_user_template("sample", str(source))

            with self.assertRaises(ValueError):
                store.use_template(template.id, str(Path(td) / "output.hwp"))

    def test_use_template_appends_source_suffix_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample.hwpx"
            source.write_text("template", encoding="utf-8")
            store = TemplateStore(base_dir=td)
            template = store.add_user_template("sample", str(source))

            output = store.use_template(template.id, str(Path(td) / "output"))

            self.assertIsNotNone(output)
            assert output is not None
            self.assertTrue(output.endswith(".hwpx"))
            self.assertTrue(Path(output).exists())

    def test_create_from_template_rejects_mismatched_suffix_before_injection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample.hwpx"
            source.write_text("template", encoding="utf-8")
            store = TemplateStore(base_dir=td)
            template = store.add_user_template("sample", str(source))

            with self.assertRaises(ValueError):
                store.create_from_template(template.id, {"name": "Kim"}, str(Path(td) / "output.hwp"))
