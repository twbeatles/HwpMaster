import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except Exception:
    QApplication = None


class TestFileListDedup(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QApplication is None:
            raise unittest.SkipTest("PySide6 is not available")
        cls._app = QApplication.instance() or QApplication([])

    def test_batch_add_deduplicates_and_emits_once(self) -> None:
        from src.ui.widgets.file_list import FileListWidget

        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "a.hwp"
            p2 = Path(td) / "b.hwpx"
            p3 = Path(td) / "c.hwp"
            p1.write_text("x", encoding="utf-8")
            p2.write_text("y", encoding="utf-8")
            p3.write_text("z", encoding="utf-8")

            widget = FileListWidget()
            self.addCleanup(widget.close)

            emitted: list[list[str]] = []
            widget.files_changed.connect(lambda files: emitted.append(list(files)))

            widget._on_files_dropped([str(p1), str(p1), str(p2)])
            self.assertEqual(widget.get_files(), [str(p1), str(p2)])
            self.assertEqual(len(emitted), 1)

            widget._on_files_dropped([str(p1), str(p2)])
            self.assertEqual(widget.get_files(), [str(p1), str(p2)])
            self.assertEqual(len(emitted), 1)

            widget._on_files_dropped([str(p2), str(p3)])
            self.assertEqual(widget.get_files(), [str(p1), str(p2), str(p3)])
            self.assertEqual(len(emitted), 2)

