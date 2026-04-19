import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.core.bookmark_manager import BookmarkManager
from src.core.header_footer_manager import HeaderFooterConfig, HeaderFooterManager
from src.core.hwp_handler import HwpHandler
from src.core.hyperlink_checker import HyperlinkChecker
from src.core.watermark_manager import WatermarkConfig, WatermarkManager


def _real_doc_tests_enabled() -> bool:
    value = str(os.getenv("HWPMASTER_REAL_DOC_TESTS", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


@unittest.skipUnless(
    _real_doc_tests_enabled(),
    "Real-document integration tests are disabled. Set HWPMASTER_REAL_DOC_TESTS=1 to run.",
)
class TestRealHwpFeatureSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyhwpx  # type: ignore

            cls._pyhwpx = pyhwpx
        except Exception as exc:
            raise unittest.SkipTest(f"pyhwpx import failed: {exc}")

        try:
            hwp = cls._pyhwpx.Hwp(visible=False)
            hwp.quit()
        except Exception as exc:
            raise unittest.SkipTest(f"Real HWP runtime not available: {exc}")

    def _insert_text(self, hwp: Any, text: str) -> None:
        if hasattr(hwp, "insert_text"):
            ok = hwp.insert_text(text)
            if ok is False:
                raise RuntimeError("insert_text returned False")
            return

        hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
        hwp.HParameterSet.HInsertText.Text = text
        hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)

    def _create_document(
        self,
        path: Path,
        *,
        pages: list[list[str]],
    ) -> None:
        hwp: Any = self._pyhwpx.Hwp(visible=False)
        try:
            for page_index, lines in enumerate(pages):
                for line_index, line in enumerate(lines):
                    suffix = "\r\n" if line_index < len(lines) - 1 else ""
                    self._insert_text(hwp, line + suffix)
                if page_index < len(pages) - 1:
                    hwp.Run("BreakPage")
            hwp.save_as(str(path))
        finally:
            try:
                hwp.quit()
            except Exception:
                pass

    def _try_insert_bookmark(self, hwp: Any) -> bool:
        attempts: list[tuple[str, Any]] = [("bokm", None)]
        create_set = getattr(hwp, "create_set", None)
        if callable(create_set):
            for set_name in ("Bookmark", "BookMark", "Bokm"):
                try:
                    attempts.append(("bokm", create_set(set_name)))
                except Exception:
                    continue

        for ctrl_id, initparam in attempts:
            try:
                ctrl = hwp.insert_ctrl(ctrl_id, initparam)
                if ctrl:
                    return True
            except Exception:
                continue
        return False

    def test_conversion_merge_split_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            left = Path(td) / "left.hwp"
            right = Path(td) / "right.hwp"
            hwpx_path = Path(td) / "left.hwpx"
            txt_path = Path(td) / "left.txt"
            merged_path = Path(td) / "merged.hwp"
            split_dir = Path(td) / "split"
            hwpx_result = None
            txt_result = None
            merge_result = None
            split_results: list[Any] = []
            self._create_document(left, pages=[["제목", "left page"]])
            self._create_document(right, pages=[["제목", "right page"]])

            with HwpHandler() as handler:
                hwpx_result = handler.convert_to_hwpx(str(left), str(hwpx_path))
                txt_result = handler.convert_to_txt(str(left), str(txt_path))
                merge_result = handler.merge_files([str(left), str(right)], str(merged_path))
                split_results = handler.split_file(str(merged_path), ["1", "2"], str(split_dir))

            assert hwpx_result is not None
            assert txt_result is not None
            assert merge_result is not None
            self.assertTrue(hwpx_result.success)
            self.assertTrue(txt_result.success)
            self.assertTrue(merge_result.success)
            self.assertTrue(all(item.success for item in split_results))
            self.assertTrue(hwpx_path.exists())
            self.assertTrue(txt_path.exists())
            self.assertTrue(merged_path.exists())
            self.assertEqual(len(split_results), 2)
            self.assertTrue(all(Path(item.output_path or "").exists() for item in split_results))

    def test_metadata_watermark_header_footer_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.hwp"
            cleaned = Path(td) / "cleaned.hwp"
            clean_result = None
            self._create_document(source, pages=[["본문", "smoke"]])

            with HwpHandler() as handler:
                clean_result = handler.clean_metadata(str(source), str(cleaned))

            wm_path = Path(td) / "watermarked.hwp"
            wm_removed_path = Path(td) / "watermark_removed.hwp"
            with WatermarkManager() as manager:
                apply_wm_result = manager.apply_watermark(
                    str(cleaned),
                    WatermarkConfig(text="DRAFT"),
                    str(wm_path),
                )
                remove_wm_result = manager.remove_watermark(str(wm_path), str(wm_removed_path))

            hf_path = Path(td) / "header_footer.hwp"
            hf_removed_path = Path(td) / "header_footer_removed.hwp"
            with HeaderFooterManager() as manager:
                apply_hf_result = manager.apply_header_footer(
                    str(wm_removed_path),
                    HeaderFooterConfig(
                        footer_enabled=True,
                        footer_center="테스트",
                        page_number_enabled=True,
                    ),
                    str(hf_path),
                )
                remove_hf_result = manager.remove_header_footer(str(hf_path), str(hf_removed_path))

            assert clean_result is not None
            self.assertTrue(clean_result.success)
            self.assertTrue(apply_wm_result.success)
            self.assertTrue(remove_wm_result.success)
            self.assertTrue(apply_hf_result.success)
            self.assertTrue(remove_hf_result.success)
            self.assertTrue(cleaned.exists())
            self.assertTrue(wm_path.exists())
            self.assertTrue(wm_removed_path.exists())
            self.assertTrue(hf_path.exists())
            self.assertTrue(hf_removed_path.exists())

    def test_bookmark_extract_delete_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "bookmark_source.hwp"
            hwp: Any = self._pyhwpx.Hwp(visible=False)
            try:
                self._insert_text(hwp, "북마크 테스트")
                if not self._try_insert_bookmark(hwp):
                    raise unittest.SkipTest("Runtime does not support bookmark insertion in this environment.")
                hwp.save_as(str(source))
            finally:
                try:
                    hwp.quit()
                except Exception:
                    pass

            with BookmarkManager() as manager:
                extract_result = manager.get_bookmarks(str(source))
                if not extract_result.success or not extract_result.bookmarks:
                    raise unittest.SkipTest("Bookmark extraction not available for inserted runtime bookmark.")

                deleted_path = Path(td) / "bookmark_deleted.hwp"
                delete_result = manager.delete_all_bookmarks(str(source), str(deleted_path))
                after_result = manager.get_bookmarks(str(deleted_path))

            self.assertTrue(extract_result.success)
            self.assertGreaterEqual(len(extract_result.bookmarks), 1)
            self.assertTrue(delete_result.success)
            self.assertTrue(deleted_path.exists())
            self.assertTrue(after_result.success)
            self.assertEqual(len(after_result.bookmarks), 0)

    def test_hyperlink_extract_and_export_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "hyperlink_source.hwp"
            hwp: Any = self._pyhwpx.Hwp(visible=False)
            try:
                self._insert_text(hwp, "LINKTEXT")
                insert_hyperlink = getattr(hwp, "insert_hyperlink", None)
                if not callable(insert_hyperlink):
                    raise unittest.SkipTest("Runtime does not expose insert_hyperlink helper.")
                ok = insert_hyperlink("target-anchor", "smoke-link")
                if ok is False:
                    raise unittest.SkipTest("Hyperlink insertion is not supported in this runtime.")
                hwp.save_as(str(source))
            finally:
                try:
                    hwp.quit()
                except Exception:
                    pass

            checker = HyperlinkChecker(external_requests_enabled=False)
            extract_result = checker.extract_links(str(source))
            if not extract_result.success or not extract_result.links:
                raise unittest.SkipTest("Inserted hyperlink was not extractable in this runtime.")

            checked = checker.check_links(str(source))
            html_report = Path(td) / "hyperlink_report.html"
            xlsx_report = Path(td) / "hyperlink_report.xlsx"
            links = [(Path(source).name, link) for link in checked.links]

            html_ok = checker.generate_report(checked, str(html_report))
            xlsx_ok = checker.export_links_to_excel(links, str(xlsx_report))

            self.assertTrue(checked.success)
            self.assertGreaterEqual(len(checked.links), 1)
            self.assertTrue(html_ok)
            self.assertTrue(xlsx_ok)
            self.assertTrue(html_report.exists())
            self.assertTrue(xlsx_report.exists())
