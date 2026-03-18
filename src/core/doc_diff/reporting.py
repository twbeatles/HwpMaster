from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import DiffReport, DiffResult


def generate_report(logger: Any, result: DiffResult, output_path: str, format: str = "html") -> bool:
    """비교 리포트 생성."""

    report = DiffReport(
        title="문서 비교 리포트",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        result=result,
    )

    try:
        content = report.to_html() if format == "html" else report.to_text()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        logger.error(f"리포트 생성 오류: {e}")
        return False
