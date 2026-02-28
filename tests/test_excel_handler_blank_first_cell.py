import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from src.core.excel_handler import ExcelHandler


class TestExcelHandlerBlankFirstCell(unittest.TestCase):
    def _make_workbook(self, path: Path) -> None:
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["A", "B"])
        ws.append([None, "keep"])
        ws.append(["x", "y"])
        ws.append(["   ", "   "])
        ws.append([None, None])
        ws.append([0, "zero"])
        wb.save(path)
        wb.close()

    def test_read_excel_keeps_rows_with_nonempty_non_first_cells(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "sample.xlsx"
            self._make_workbook(file_path)

            result = ExcelHandler.read_excel(str(file_path))
            self.assertTrue(result.success)
            self.assertEqual(result.row_count, 3)
            self.assertEqual(result.data[0]["A"], "")
            self.assertEqual(result.data[0]["B"], "keep")
            self.assertEqual(result.data[1]["A"], "x")
            self.assertEqual(result.data[2]["A"], 0)

    def test_read_excel_streaming_keeps_rows_with_nonempty_non_first_cells(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "sample.xlsx"
            self._make_workbook(file_path)

            chunks = list(ExcelHandler.read_excel_streaming(str(file_path), chunk_size=1))
            rows = [row for chunk in chunks for row in chunk]

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["A"], "")
            self.assertEqual(rows[0]["B"], "keep")
            self.assertEqual(rows[1]["A"], "x")
            self.assertEqual(rows[2]["A"], 0)


if __name__ == "__main__":
    unittest.main()
