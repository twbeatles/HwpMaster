from __future__ import annotations

import logging

from .comparator import compare_lines
from .extractor import extract_text
from .models import DiffResult
from .reporting import generate_report


class DocDiff:
    """
    문서 비교기
    두 HWP 파일의 텍스트 차이 분석
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def extract_text(self, file_path: str) -> list[str]:
        return extract_text(self._logger, file_path)

    def compare(self, file1_path: str, file2_path: str) -> DiffResult:
        try:
            lines1 = self.extract_text(file1_path)
            lines2 = self.extract_text(file2_path)
            return compare_lines(lines1, lines2, file1_path, file2_path)
        except Exception as e:
            return DiffResult(
                success=False,
                file1_path=file1_path,
                file2_path=file2_path,
                error_message=str(e),
            )

    def _compare_lines(
        self,
        lines1: list[str],
        lines2: list[str],
        file1_path: str,
        file2_path: str,
    ) -> DiffResult:
        return compare_lines(lines1, lines2, file1_path, file2_path)

    def compare_text(self, text1: str, text2: str) -> DiffResult:
        lines1 = text1.split("\n")
        lines2 = text2.split("\n")
        return compare_lines(lines1, lines2, "text1", "text2")

    def generate_report(self, result: DiffResult, output_path: str, format: str = "html") -> bool:
        return generate_report(self._logger, result, output_path, format=format)
