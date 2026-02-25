import importlib
import sys
import unittest


class TestPagesLazyImport(unittest.TestCase):
    def _reload_pages_package(self):
        for name in list(sys.modules):
            if name == "src.ui.pages" or name.startswith("src.ui.pages."):
                sys.modules.pop(name, None)
        return importlib.import_module("src.ui.pages")

    def test_lazy_module_loaded_on_attribute_access(self) -> None:
        pages = self._reload_pages_package()

        self.assertIn("TemplatePage", getattr(pages, "__all__", []))
        self.assertIn("ActionConsolePage", getattr(pages, "__all__", []))
        self.assertNotIn("src.ui.pages.template_page", sys.modules)

        cls = pages.TemplatePage

        self.assertEqual(cls.__name__, "TemplatePage")
        self.assertIn("src.ui.pages.template_page", sys.modules)

    def test_unknown_attribute_raises(self) -> None:
        pages = self._reload_pages_package()
        with self.assertRaises(AttributeError):
            _ = pages.NotARealPage

