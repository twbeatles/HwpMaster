import unittest

from src.utils.qss_renderer import build_stylesheet


class TestQssRender(unittest.TestCase):
    def test_build_stylesheet_dark_has_no_tokens_left(self) -> None:
        css = build_stylesheet("Dark (기본)")
        self.assertNotIn("{{", css)
        self.assertIn("#0d1117", css)
        self.assertIn("#8957e5", css)

    def test_build_stylesheet_light_differs(self) -> None:
        css = build_stylesheet("Light")
        self.assertNotIn("{{", css)
        self.assertIn("#ffffff", css.lower())

