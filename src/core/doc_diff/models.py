from __future__ import annotations

import html as html_lib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ChangeType(Enum):
    """변경 타입"""

    ADDED = "추가"
    DELETED = "삭제"
    MODIFIED = "수정"
    UNCHANGED = "동일"


@dataclass
class DiffLine:
    """변경 라인"""

    line_number: int
    change_type: ChangeType
    original_text: str = ""
    new_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "line": self.line_number,
            "type": self.change_type.value,
            "original": self.original_text,
            "new": self.new_text,
        }


@dataclass
class DiffResult:
    """비교 결과"""

    success: bool
    file1_path: str
    file2_path: str
    file1_lines: int = 0
    file2_lines: int = 0
    added_count: int = 0
    deleted_count: int = 0
    modified_count: int = 0
    changes: list[DiffLine] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def similarity_ratio(self) -> float:
        """유사도 비율 (0~1)"""

        total = self.file1_lines + self.file2_lines
        if total == 0:
            return 1.0
        unchanged = total - (self.added_count + self.deleted_count + self.modified_count * 2)
        return max(0.0, unchanged / total)

    @property
    def total_changes(self) -> int:
        return self.added_count + self.deleted_count + self.modified_count


@dataclass
class DiffReport:
    """비교 리포트"""

    title: str
    generated_at: str
    result: DiffResult

    def to_html(self) -> str:
        """HTML 리포트 생성"""

        title = html_lib.escape(str(self.title))
        generated_at = html_lib.escape(str(self.generated_at))
        file1_name = html_lib.escape(Path(self.result.file1_path).name)
        file2_name = html_lib.escape(Path(self.result.file2_path).name)
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 20px; }}
        .header {{ background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }}
        .added {{ background: #d4edda; }}
        .deleted {{ background: #f8d7da; }}
        .modified {{ background: #fff3cd; }}
        .diff-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .diff-table th, .diff-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .diff-table th {{ background: #333; color: white; }}
        .line-added {{ background: #d4edda; }}
        .line-deleted {{ background: #f8d7da; }}
        .line-modified {{ background: #fff3cd; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📄 문서 비교 리포트</h1>
        <p>생성일: {generated_at}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>파일 1</h3>
            <p>{file1_name}</p>
            <p>{self.result.file1_lines}줄</p>
        </div>
        <div class="stat-card">
            <h3>파일 2</h3>
            <p>{file2_name}</p>
            <p>{self.result.file2_lines}줄</p>
        </div>
        <div class="stat-card added">
            <h3>추가</h3>
            <p style="font-size: 24px; font-weight: bold;">+{self.result.added_count}</p>
        </div>
        <div class="stat-card deleted">
            <h3>삭제</h3>
            <p style="font-size: 24px; font-weight: bold;">-{self.result.deleted_count}</p>
        </div>
        <div class="stat-card modified">
            <h3>수정</h3>
            <p style="font-size: 24px; font-weight: bold;">~{self.result.modified_count}</p>
        </div>
        <div class="stat-card">
            <h3>유사도</h3>
            <p style="font-size: 24px; font-weight: bold;">{self.result.similarity_ratio * 100:.1f}%</p>
        </div>
    </div>

    <h2>변경 내역</h2>
    <table class="diff-table">
        <tr>
            <th>줄</th>
            <th>유형</th>
            <th>원본 (파일 1)</th>
            <th>변경 (파일 2)</th>
        </tr>
"""
        for change in self.result.changes[:100]:
            row_class = {
                ChangeType.ADDED: "line-added",
                ChangeType.DELETED: "line-deleted",
                ChangeType.MODIFIED: "line-modified",
            }.get(change.change_type, "")

            html += f"""
        <tr class="{row_class}">
            <td>{change.line_number}</td>
            <td>{change.change_type.value}</td>
            <td>{html_lib.escape(change.original_text[:100])}</td>
            <td>{html_lib.escape(change.new_text[:100])}</td>
        </tr>
"""

        if len(self.result.changes) > 100:
            html += f"""
        <tr>
            <td colspan="4" style="text-align: center;">... 외 {len(self.result.changes) - 100}건</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        return html

    def to_text(self) -> str:
        """텍스트 리포트 생성"""

        lines = [
            "=" * 60,
            "📄 문서 비교 리포트",
            "=" * 60,
            f"생성일: {self.generated_at}",
            "",
            f"파일 1: {self.result.file1_path} ({self.result.file1_lines}줄)",
            f"파일 2: {self.result.file2_path} ({self.result.file2_lines}줄)",
            "",
            f"추가: +{self.result.added_count}",
            f"삭제: -{self.result.deleted_count}",
            f"수정: ~{self.result.modified_count}",
            f"유사도: {self.result.similarity_ratio * 100:.1f}%",
            "",
            "-" * 60,
            "변경 내역",
            "-" * 60,
        ]

        for change in self.result.changes[:50]:
            type_symbol = {
                ChangeType.ADDED: "+",
                ChangeType.DELETED: "-",
                ChangeType.MODIFIED: "~",
            }.get(change.change_type, " ")

            lines.append(f"[{change.line_number:4d}] {type_symbol} {change.original_text[:60]}")
            if change.new_text and change.change_type == ChangeType.MODIFIED:
                lines.append(f"       → {change.new_text[:60]}")

        return "\n".join(lines)
