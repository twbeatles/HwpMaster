import unittest

from src.core.smart_toc import SmartTOC, TocEntry, TocResult


class TestSmartTocPaging(unittest.TestCase):
    def test_extract_from_text_uses_form_feed_pages(self) -> None:
        toc = SmartTOC()
        text = "1. 개요\n본문\n\f2. 상세\n가. 세부 항목\n"

        result = toc.extract_from_text(text)

        self.assertTrue(result.success)
        self.assertEqual(result.analysis_mode, "pattern_only")
        self.assertGreaterEqual(len(result.entries), 3)
        self.assertTrue(all(entry.page >= 1 for entry in result.entries))

        by_text = {entry.text: entry for entry in result.entries}
        self.assertEqual(by_text["1. 개요"].page, 1)
        self.assertEqual(by_text["2. 상세"].page, 2)
        self.assertEqual(by_text["가. 세부 항목"].page, 2)

    def test_to_html_escapes_text_and_includes_page_numbers(self) -> None:
        result = TocResult(
            success=True,
            file_path="sample.hwp",
            entries=[TocEntry(level=1, text="<제목 & 본문>", page=3)],
        )

        html = result.to_html()

        self.assertIn("&lt;제목 &amp; 본문&gt;", html)
        self.assertIn(">3<", html)

    def test_align_style_hints_to_lines_matches_in_order_and_reports_stats(self) -> None:
        toc = SmartTOC()
        page_lines = [
            (1, 1, "1. 개요"),
            (2, 1, "본문"),
            (3, 2, "2.   상세"),
            (4, 2, "가.\t세부"),
        ]
        candidates = [
            ("1. 개요", 16.0, True),
            ("2. 상세", 16.0, True),
            ("가. 세부", 14.0, True),
            ("없는 제목", 12.0, True),
        ]

        hints, total, matched, missed = toc._align_style_hints_to_lines(page_lines, candidates)

        self.assertEqual(total, 4)
        self.assertEqual(matched, 3)
        self.assertEqual(missed, 1)
        self.assertEqual(hints[1], (16.0, True))
        self.assertEqual(hints[3], (16.0, True))
        self.assertEqual(hints[4], (14.0, True))


if __name__ == "__main__":
    unittest.main()
