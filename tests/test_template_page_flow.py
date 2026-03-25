import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except Exception:
    QApplication = None

from src.core.template_store.models import TemplateInfo


class _FakeStore:
    def __init__(self, template: TemplateInfo) -> None:
        self.template = template
        self.used_calls: list[tuple[str, str]] = []
        self.created_calls: list[tuple[str, dict[str, str], str]] = []

    def get_categories(self) -> list[str]:
        return []

    def get_all_templates(self) -> list[TemplateInfo]:
        return []

    def get_templates_by_category(self, category: str) -> list[TemplateInfo]:
        return []

    def get_template(self, template_id: str) -> TemplateInfo:
        assert template_id == self.template.id
        return self.template

    def use_template(self, template_id: str, output_path: str) -> str:
        self.used_calls.append((template_id, output_path))
        Path(output_path).write_text("copy", encoding="utf-8")
        return output_path

    def create_from_template(self, template_id: str, data: dict[str, str], output_path: str) -> str:
        self.created_calls.append((template_id, data, output_path))
        Path(output_path).write_text("create", encoding="utf-8")
        return output_path

    def register_builtin_template_file(self, template_id: str, file_path: str) -> bool:
        return True


class TestTemplatePageFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QApplication is None:
            raise unittest.SkipTest("PySide6 is not available")
        cls._app = QApplication.instance() or QApplication([])

    def test_fields_template_uses_create_from_template(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            from src.utils.settings import SettingsManager

            settings = SettingsManager(config_dir=td)
            source = Path(td) / "sample.hwpx"
            source.write_text("template", encoding="utf-8")
            template = TemplateInfo(
                id="tpl",
                name="보고서",
                description="desc",
                category="기타",
                file_path=str(source),
                fields=["name"],
            )
            store = _FakeStore(template)

            with (
                patch("src.ui.pages.template_page.TemplateStore", return_value=store),
                patch("src.ui.pages.template_page.get_settings_manager", return_value=settings),
                patch("src.ui.pages.template_page.QFileDialog.getSaveFileName", return_value=(str(Path(td) / "output.hwpx"), "")),
                patch("src.ui.pages.template_page.QMessageBox.information"),
                patch("src.ui.pages.template_page.record_task_summary"),
            ):
                from src.ui.pages.template_page import TemplatePage

                page = TemplatePage()
                page._prompt_template_fields = lambda _template: {"name": "Kim"}  # type: ignore[method-assign]
                page._on_template_clicked("tpl")

            self.assertEqual(len(store.created_calls), 1)
            self.assertEqual(len(store.used_calls), 0)

    def test_plain_template_uses_copy_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            from src.utils.settings import SettingsManager

            settings = SettingsManager(config_dir=td)
            source = Path(td) / "sample.hwp"
            source.write_text("template", encoding="utf-8")
            template = TemplateInfo(
                id="tpl",
                name="공문",
                description="desc",
                category="기타",
                file_path=str(source),
                fields=[],
            )
            store = _FakeStore(template)

            with (
                patch("src.ui.pages.template_page.TemplateStore", return_value=store),
                patch("src.ui.pages.template_page.get_settings_manager", return_value=settings),
                patch("src.ui.pages.template_page.QFileDialog.getSaveFileName", return_value=(str(Path(td) / "output.hwp"), "")),
                patch("src.ui.pages.template_page.QMessageBox.information"),
                patch("src.ui.pages.template_page.record_task_summary"),
            ):
                from src.ui.pages.template_page import TemplatePage

                page = TemplatePage()
                page._on_template_clicked("tpl")

            self.assertEqual(len(store.used_calls), 1)
            self.assertEqual(len(store.created_calls), 0)
