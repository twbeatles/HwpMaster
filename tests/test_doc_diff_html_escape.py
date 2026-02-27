import unittest

from src.core.doc_diff import ChangeType, DiffLine, DiffReport, DiffResult


class TestDocDiffHtmlEscape(unittest.TestCase):
    def test_html_report_escapes_untrusted_text(self) -> None:
        result = DiffResult(
            success=True,
            file1_path=r"C:\tmp\left<script>.hwp",
            file2_path=r"C:\tmp\right<b>.hwp",
            file1_lines=1,
            file2_lines=1,
            changes=[
                DiffLine(
                    line_number=1,
                    change_type=ChangeType.MODIFIED,
                    original_text="<script>alert(1)</script>",
                    new_text="<b>hello</b>",
                )
            ],
            modified_count=1,
        )
        report = DiffReport(
            title="<b>bad title</b>",
            generated_at="2026-02-27 <script>now</script>",
            result=result,
        )

        html = report.to_html()

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;b&gt;hello&lt;/b&gt;", html)
        self.assertIn("left&lt;script&gt;.hwp", html)
        self.assertIn("right&lt;b&gt;.hwp", html)
        self.assertIn("&lt;b&gt;bad title&lt;/b&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)


if __name__ == "__main__":
    unittest.main()
