import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except Exception:
    QApplication = None


class TestMainWindowLazyPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QApplication is None:
            raise unittest.SkipTest("PySide6 is not available")
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from src.utils.settings import SettingsManager

        self._tmp = tempfile.TemporaryDirectory()
        self._settings = SettingsManager(config_dir=self._tmp.name)
        self._settings.set("default_convert_format", "HWPX")
        self._settings.set("sidebar_collapsed", True)
        self._settings.set("window_width", 1320)
        self._settings.set("window_height", 860)

        self._patcher = patch("src.ui.main_window.get_settings_manager", return_value=self._settings)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self._settings.flush)

        from src.ui.main_window import MainWindow

        self.window = MainWindow()
        self.addCleanup(self.window.close)

    def test_advanced_page_is_created_lazily(self) -> None:
        self.assertEqual(self.window.page_stack.count(), self.window._TOTAL_PAGE_COUNT)
        self.assertIsNone(self.window.hyperlink_page)
        self.assertNotIn(15, self.window._lazy_loaded)

        self.window._on_page_changed(15)

        self.assertIsNotNone(self.window.hyperlink_page)
        self.assertIn(15, self.window._lazy_loaded)
        self.assertEqual(self.window.page_stack.currentIndex(), 15)

        first = self.window.hyperlink_page
        self.window._on_page_changed(15)
        self.assertIs(first, self.window.hyperlink_page)

    def test_settings_are_applied_on_startup(self) -> None:
        self.assertTrue(self.window.sidebar.is_collapsed)
        checked = [b.text() for b in self.window.convert_page.format_buttons if b.isChecked()]
        self.assertEqual(checked, ["HWPX"])
