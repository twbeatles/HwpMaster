import unittest

from src.utils.qss_renderer import build_stylesheet
from src.utils.theme_manager import THEME_PRESETS


class TestQssRender(unittest.TestCase):
    def test_build_stylesheet_dark_has_no_tokens_left(self) -> None:
        css = build_stylesheet("Dark (기본)")
        dark = THEME_PRESETS["Dark (기본)"]
        self.assertNotIn("{{", css)
        self.assertIn(dark.background.lower(), css.lower())
        self.assertIn(dark.primary.lower(), css.lower())
        self.assertIn(dark.text_primary.lower(), css.lower())

    def test_build_stylesheet_light_differs(self) -> None:
        dark_css = build_stylesheet("Dark (기본)")
        css = build_stylesheet("Light")
        self.assertNotIn("{{", css)
        self.assertIn("#ffffff", css.lower())
        self.assertNotEqual(css, dark_css)

