from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any


def extract_text(logger: Any, file_path: str) -> list[str]:
    """HWP 파일에서 텍스트 추출."""

    lines: list[str] = []

    try:
        from src.core.hwp_handler import HwpHandler

        with HwpHandler() as handler:
            handler._ensure_hwp()
            hwp = handler._hwp

            hwp.open(file_path)
            hwp.Run("SelectAll")
            text = hwp.GetTextFile("TEXT", "")
            hwp.Run("Cancel")

            if text:
                lines = text.split("\n")
            else:
                tmp_path = ""
                with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    hwp.save_as(tmp_path, format="TEXT")

                    with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.read().split("\n")
                finally:
                    if tmp_path:
                        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"텍스트 추출 오류: {e}")

    return lines
