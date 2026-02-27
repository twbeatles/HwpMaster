import tempfile
import unittest
from pathlib import Path

from src.core.template_store import TemplateStore


class TestTemplateStoreUuid(unittest.TestCase):
    def test_add_user_template_generates_unique_uuid_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample.hwp"
            source.write_text("dummy", encoding="utf-8")
            store = TemplateStore(base_dir=td)

            ids: set[str] = set()
            for idx in range(30):
                tpl = store.add_user_template(
                    name=f"sample-{idx}",
                    file_path=str(source),
                    description="test",
                )
                self.assertNotIn(tpl.id, ids)
                self.assertTrue(tpl.id.startswith("user_"))
                self.assertEqual(len(tpl.id), len("user_") + 32)
                ids.add(tpl.id)

            self.assertEqual(len(ids), 30)


if __name__ == "__main__":
    unittest.main()
