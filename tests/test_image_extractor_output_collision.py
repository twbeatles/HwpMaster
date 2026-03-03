import tempfile
import unittest
from pathlib import Path

from src.core.image_extractor import ExtractResult, ImageExtractor


class _SpyImageExtractor(ImageExtractor):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str, str]] = []

    def _ensure_hwp(self) -> None:
        return None

    def extract_images(
        self,
        source_path: str,
        output_dir: str,
        prefix: str = "",
        progress_callback=None,
    ) -> ExtractResult:
        self.calls.append((source_path, output_dir, prefix))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return ExtractResult(success=True, source_path=source_path, images=[])


class TestImageExtractorOutputCollision(unittest.TestCase):
    def test_batch_extract_uses_per_file_subdirs_and_passes_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            output_dir = td_path / "out"
            files = [
                str(td_path / "a" / "report.hwp"),
                str(td_path / "b" / "report.hwp"),
            ]

            extractor = _SpyImageExtractor()
            results = extractor.batch_extract(files, str(output_dir), prefix="img")

            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.success for r in results))
            self.assertEqual(len(extractor.calls), 2)

            first_out = Path(extractor.calls[0][1]).name
            second_out = Path(extractor.calls[1][1]).name
            self.assertEqual(first_out, "report")
            self.assertEqual(second_out, "report_1")
            self.assertEqual(extractor.calls[0][2], "img")
            self.assertEqual(extractor.calls[1][2], "img")


if __name__ == "__main__":
    unittest.main()

