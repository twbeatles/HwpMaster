import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QDialog
except Exception:
    QApplication = None
    QDialog = None

from src.core.template_store import TemplateStore, TemplateStoreError
from src.core.template_store.models import TemplateInfo


class _AddFailStore:
    def get_categories(self) -> list[str]:
        return []

    def get_all_templates(self) -> list[TemplateInfo]:
        return []

    def get_templates_by_category(self, category: str) -> list[TemplateInfo]:
        return []

    def add_user_template(self, **kwargs) -> TemplateInfo:
        raise TemplateStoreError("copy failed")


class _UseFailStore:
    def __init__(self, template: TemplateInfo) -> None:
        self._template = template

    def get_categories(self) -> list[str]:
        return []

    def get_all_templates(self) -> list[TemplateInfo]:
        return []

    def get_templates_by_category(self, category: str) -> list[TemplateInfo]:
        return []

    def get_template(self, template_id: str) -> TemplateInfo:
        return self._template

    def use_template(self, template_id: str, output_path: str) -> str:
        raise TemplateStoreError("use failed")


class _FakeAddDialog:
    def __init__(self, parent=None) -> None:
        return

    def exec(self) -> int:
        assert QDialog is not None
        return QDialog.DialogCode.Accepted

    def get_data(self) -> dict[str, str]:
        return {
            "name": "보고서",
            "file_path": "C:/temp/sample.hwp",
            "category": "기타",
            "description": "desc",
        }


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class TestTemplateStoreErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app_cls = QApplication
        assert app_cls is not None
        cls._app = app_cls.instance() or app_cls([])

    def test_add_user_template_wraps_copy_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample.hwp"
            source.write_text("template", encoding="utf-8")
            store = TemplateStore(base_dir=td)

            with patch("src.core.template_store.service.shutil.copy2", side_effect=OSError("disk full")):
                with self.assertRaises(TemplateStoreError):
                    store.add_user_template("sample", str(source))

    def test_template_page_routes_add_error_to_message_box(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            from src.utils.settings import SettingsManager

            settings = SettingsManager(config_dir=td)
            with (
                patch("src.ui.pages.template_page.TemplateStore", return_value=_AddFailStore()),
                patch("src.ui.pages.template_page.AddTemplateDialog", _FakeAddDialog),
                patch("src.ui.pages.template_page.get_settings_manager", return_value=settings),
                patch("src.ui.pages.template_page.QMessageBox.warning") as warning_mock,
            ):
                from src.ui.pages.template_page import TemplatePage

                page = TemplatePage()
                page._add_template()

            warning_mock.assert_called()

    def test_template_page_routes_use_error_to_message_box(self) -> None:
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
            )
            with (
                patch("src.ui.pages.template_page.TemplateStore", return_value=_UseFailStore(template)),
                patch("src.ui.pages.template_page.get_settings_manager", return_value=settings),
                patch("src.ui.pages.template_page.QFileDialog.getSaveFileName", return_value=(str(Path(td) / "out.hwp"), "")),
                patch("src.ui.pages.template_page.QMessageBox.warning") as warning_mock,
            ):
                from src.ui.pages.template_page import TemplatePage

                page = TemplatePage()
                page._on_template_clicked("tpl")

            warning_mock.assert_called()
