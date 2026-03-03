import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.doc_diff import DocDiff


class _FakeHwp:
    def open(self, path: str) -> None:
        return None

    def Run(self, action_id: str) -> None:  # noqa: N802
        return None

    def GetTextFile(self, _fmt: str, _opt: str) -> str:  # noqa: N802
        return ""

    def save_as(self, output_path: str, format: str = "TEXT") -> None:
        raise RuntimeError("save failed")


class _FakeHandler:
    def __init__(self) -> None:
        self._hwp = _FakeHwp()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def _ensure_hwp(self) -> None:
        return None


class _TmpContext:
    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self):
        self._path.write_text("", encoding="utf-8")

        class _Tmp:
            def __init__(self, name: str) -> None:
                self.name = name

        return _Tmp(str(self._path))

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestDocDiffTempfileCleanup(unittest.TestCase):
    def test_extract_text_cleanup_when_fallback_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp_txt = Path(td) / "doc_diff_tmp.txt"

            def _fake_named_tempfile(*args, **kwargs):
                return _TmpContext(temp_txt)

            with (
                patch("src.core.hwp_handler.HwpHandler", _FakeHandler),
                patch("tempfile.NamedTemporaryFile", side_effect=_fake_named_tempfile),
            ):
                diff = DocDiff()
                lines = diff.extract_text("input.hwp")

            self.assertEqual(lines, [])
            self.assertFalse(temp_txt.exists())


if __name__ == "__main__":
    unittest.main()

