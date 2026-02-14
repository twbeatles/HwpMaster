import os
import tempfile
import unittest
from pathlib import Path


from src.utils.output_paths import ensure_dir, resolve_output_path


class TestOutputPaths(unittest.TestCase):
    def test_ensure_dir_creates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a" / "b"
            out = ensure_dir(str(p))
            self.assertTrue(Path(out).exists())
            self.assertTrue(Path(out).is_dir())

    def test_resolve_output_path_no_collision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            src = Path(td) / "file.hwp"
            src.write_text("x", encoding="utf-8")

            out = resolve_output_path(str(out_dir), str(src))
            self.assertTrue(out.endswith("file.hwp"))

    def test_resolve_output_path_collision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            src = Path(td) / "file.hwp"
            src.write_text("x", encoding="utf-8")

            first = resolve_output_path(str(out_dir), str(src))
            Path(first).parent.mkdir(parents=True, exist_ok=True)
            Path(first).write_text("y", encoding="utf-8")

            second = resolve_output_path(str(out_dir), str(src))
            self.assertNotEqual(first, second)
            self.assertTrue(second.endswith("file_1.hwp"))

    def test_resolve_output_path_new_ext(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            src = Path(td) / "file.hwp"
            src.write_text("x", encoding="utf-8")

            out = resolve_output_path(str(out_dir), str(src), new_ext="pdf")
            self.assertTrue(out.endswith("file.pdf"))

