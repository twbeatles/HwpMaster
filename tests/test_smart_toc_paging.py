import unittest

from src.core.smart_toc import SmartTOC


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


if __name__ == "__main__":
    unittest.main()
