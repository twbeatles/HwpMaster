import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.core.doc_diff import DocDiff
from src.core.smart_toc import SmartTOC


def _real_doc_tests_enabled() -> bool:
    value = str(os.getenv("HWPMASTER_REAL_DOC_TESTS", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


@unittest.skipUnless(
    _real_doc_tests_enabled(),
    "Real-document integration tests are disabled. Set HWPMASTER_REAL_DOC_TESTS=1 to run.",
)
class TestRealHwpDocDiffSmartToc(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyhwpx  # type: ignore

            cls._pyhwpx = pyhwpx
        except Exception as e:
            raise unittest.SkipTest(f"pyhwpx import failed: {e}")

        try:
            hwp = cls._pyhwpx.Hwp(visible=False)
            hwp.quit()
        except Exception as e:
            raise unittest.SkipTest(f"Real HWP runtime not available: {e}")

    def _create_document(self, path: Path, lines: list[str]) -> None:
        hwp: Any = self._pyhwpx.Hwp(visible=False)
        try:
            hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
            hwp.HParameterSet.HInsertText.Text = "\r\n".join(lines) + "\r\n"
            hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
            hwp.save_as(str(path))
        finally:
            try:
                hwp.quit()
            except Exception:
                pass

    def test_doc_diff_compare_real_documents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file1 = Path(td) / "left.hwp"
            file2 = Path(td) / "right.hwp"
            self._create_document(file1, ["제목", "alpha", "beta"])
            self._create_document(file2, ["제목", "ALPHA", "beta", "gamma"])

            result = DocDiff().compare(str(file1), str(file2))

            self.assertTrue(result.success)
            self.assertGreaterEqual(result.modified_count, 1)
            self.assertGreaterEqual(result.added_count, 1)

    def test_smart_toc_extract_real_document(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "toc_source.hwp"
            self._create_document(
                source,
                [
                    "1. 개요",
                    "본문 설명",
                    "2. 상세",
                    "가. 세부 항목",
                    "추가 본문",
                ],
            )

            result = SmartTOC().extract_toc(str(source))

            self.assertTrue(result.success)
            titles = [entry.text for entry in result.entries]
            self.assertTrue(any(t.startswith("1.") for t in titles))
            self.assertTrue(any(t.startswith("2.") for t in titles))
            self.assertTrue(any(t.startswith("가.") for t in titles))


if __name__ == "__main__":
    unittest.main()

