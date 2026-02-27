import tempfile
import unittest
from pathlib import Path

from src.utils.worker import DataInjectWorker


class TestDataInjectWorkerCsv(unittest.TestCase):
    def test_iter_csv_rows_skips_only_all_empty_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "rows.csv"
            csv_path.write_text(
                "A,B\n"
                ",keep_me\n"
                ",\n"
                "x,\n",
                encoding="utf-8",
            )

            rows = list(DataInjectWorker._iter_csv_rows(csv_path))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["A"], "")
            self.assertEqual(rows[0]["B"], "keep_me")
            self.assertEqual(rows[1]["A"], "x")

    def test_count_empty_csv_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "rows.csv"
            csv_path.write_text(
                "A,B\n"
                " , \n"
                "foo,bar\n"
                ",\n",
                encoding="utf-8",
            )
            self.assertEqual(DataInjectWorker._count_empty_csv_rows(csv_path), 2)


if __name__ == "__main__":
    unittest.main()
