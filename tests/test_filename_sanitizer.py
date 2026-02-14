import unittest


from src.utils.filename_sanitizer import sanitize_filename


class TestFilenameSanitizer(unittest.TestCase):
    def test_replaces_invalid_chars_and_trims(self) -> None:
        self.assertEqual(sanitize_filename('a<b>:"c"|d?.txt'), "a_b___c__d_.txt")
        self.assertEqual(sanitize_filename(" name. "), "name")
        self.assertEqual(sanitize_filename("a..."), "a")

    def test_reserved_device_names(self) -> None:
        self.assertEqual(sanitize_filename("CON"), "CON_")
        self.assertEqual(sanitize_filename("con.txt"), "con.txt_")
        self.assertEqual(sanitize_filename("LPT1"), "LPT1_")

    def test_empty_becomes_output(self) -> None:
        self.assertEqual(sanitize_filename("   "), "output")

    def test_length_limit_keeps_extension(self) -> None:
        out = sanitize_filename("a" * 50 + ".hwp", max_length=10)
        self.assertTrue(out.endswith(".hwp"))
        self.assertLessEqual(len(out), 10)
