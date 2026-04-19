import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except Exception:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class TestHyperlinkPageState(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app_cls = QApplication
        assert app_cls is not None
        cls._app = app_cls.instance() or app_cls([])

    def test_on_error_restores_buttons_and_clears_cached_links(self) -> None:
        from src.ui.pages.hyperlink_page import HyperlinkPage

        page = HyperlinkPage()
        page.progress.setVisible(True)
        page.scan_btn.setEnabled(False)
        page.export_btn.setEnabled(False)
        page._links = [("a.hwp", object())]  # type: ignore[list-item]

        page._on_error("boom")

        self.assertFalse(page.progress.isVisible())
        self.assertTrue(page.scan_btn.isEnabled())
        self.assertFalse(page.export_btn.isEnabled())
        self.assertEqual(page._links, [])
