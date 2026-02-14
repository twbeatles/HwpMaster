import tempfile
import unittest
from pathlib import Path
import zipfile

from src.core.image_extractor import ImageExtractor


class TestHwpxZipExtract(unittest.TestCase):
    def test_extract_from_hwpx_zip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            hwpx = td_path / "doc.hwpx"
            out_dir = td_path / "out"
            out_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(hwpx, "w") as zf:
                zf.writestr("BinData/image1.png", b"\x89PNG\r\n\x1a\nxxxx")
                zf.writestr("BinData/image2.jpg", b"\xff\xd8\xffxxxx")
                zf.writestr("Contents/content.xml", "<xml/>")

            extractor = ImageExtractor()
            images = extractor._extract_from_hwpx_zip(hwpx, out_dir, prefix="", source_stem="doc")

            self.assertEqual(len(images), 2)
            self.assertTrue((out_dir / "doc_001.png").exists())
            self.assertTrue((out_dir / "doc_002.jpg").exists())

