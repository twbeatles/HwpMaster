import tempfile
import unittest

from src.core.template_store import TemplateStore


class _SaveCountTemplateStore(TemplateStore):
    def __init__(self, base_dir: str) -> None:
        self.save_calls = 0
        super().__init__(base_dir=base_dir)

    def _save_metadata(self) -> None:
        self.save_calls += 1
        super()._save_metadata()


class TestTemplateStoreInitSave(unittest.TestCase):
    def test_init_saves_only_when_builtin_metadata_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            first = _SaveCountTemplateStore(td)
            self.assertEqual(first.save_calls, 1)

            second = _SaveCountTemplateStore(td)
            self.assertEqual(second.save_calls, 0)

