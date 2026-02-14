import unittest


from src.core.doc_diff import DocDiff, ChangeType


class TestDocDiffCounts(unittest.TestCase):
    def test_compare_text_modified_counts(self) -> None:
        diff = DocDiff()
        res = diff.compare_text("a\nb\nc\n", "a\nB\nc\n")
        self.assertTrue(res.success)
        self.assertEqual(res.added_count, 0)
        self.assertEqual(res.deleted_count, 0)
        self.assertEqual(res.modified_count, 1)
        self.assertTrue(any(c.change_type == ChangeType.MODIFIED for c in res.changes))

    def test_compare_text_replace_len_mismatch_counts(self) -> None:
        diff = DocDiff()
        res = diff.compare_text("a\nb\nc\n", "a\nB\nc\nD\n")
        self.assertTrue(res.success)
        self.assertEqual(res.deleted_count, 0)
        self.assertEqual(res.modified_count, 1)
        self.assertEqual(res.added_count, 1)


if __name__ == "__main__":
    unittest.main()

