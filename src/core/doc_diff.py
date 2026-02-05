"""
Doc Diff Module
문서 비교기 - 두 HWP 파일의 텍스트 차이 분석

Author: HWP Master
"""

import difflib
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


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
    
    def to_dict(self) -> dict:
        return {
            "line": self.line_number,
            "type": self.change_type.value,
            "original": self.original_text,
            "new": self.new_text
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
        return max(0, unchanged / total)
    
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
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
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
        <p>생성일: {self.generated_at}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>파일 1</h3>
            <p>{Path(self.result.file1_path).name}</p>
            <p>{self.result.file1_lines}줄</p>
        </div>
        <div class="stat-card">
            <h3>파일 2</h3>
            <p>{Path(self.result.file2_path).name}</p>
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
        for change in self.result.changes[:100]:  # 최대 100개
            row_class = {
                ChangeType.ADDED: "line-added",
                ChangeType.DELETED: "line-deleted",
                ChangeType.MODIFIED: "line-modified",
            }.get(change.change_type, "")
            
            html += f"""
        <tr class="{row_class}">
            <td>{change.line_number}</td>
            <td>{change.change_type.value}</td>
            <td>{change.original_text[:100]}</td>
            <td>{change.new_text[:100]}</td>
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


class DocDiff:
    """
    문서 비교기
    두 HWP 파일의 텍스트 차이 분석
    """
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
    
    def extract_text(self, file_path: str) -> list[str]:
        """
        HWP 파일에서 텍스트 추출
        
        Args:
            file_path: HWP 파일 경로
        
        Returns:
            텍스트 라인 목록
        """
        lines: list[str] = []
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                # 전체 텍스트 추출 (pyhwpx Run 액션 사용)
                hwp.Run("SelectAll")
                text = hwp.GetTextFile("TEXT", "")
                hwp.Run("Cancel")
                
                if text:
                    lines = text.split('\n')
                else:
                    # 대체 방법: 텍스트 파일로 변환 후 읽기
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    hwp.save_as(tmp_path, format="TEXT")
                    
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.read().split('\n')
                    
                    Path(tmp_path).unlink(missing_ok=True)
                    
        except Exception as e:
            self._logger.error(f"텍스트 추출 오류: {e}")
        
        return lines
    
    def compare(
        self,
        file1_path: str,
        file2_path: str
    ) -> DiffResult:
        """
        두 파일 비교
        
        Args:
            file1_path: 원본 파일 경로
            file2_path: 비교 파일 경로
        
        Returns:
            DiffResult
        """
        try:
            # 텍스트 추출
            lines1 = self.extract_text(file1_path)
            lines2 = self.extract_text(file2_path)
            
            result = DiffResult(
                success=True,
                file1_path=file1_path,
                file2_path=file2_path,
                file1_lines=len(lines1),
                file2_lines=len(lines2)
            )
            
            # difflib을 사용한 비교
            differ = difflib.unified_diff(
                lines1, lines2,
                fromfile=file1_path,
                tofile=file2_path,
                lineterm=''
            )
            
            line_num = 0
            for line in differ:
                if line.startswith('@@'):
                    # 위치 정보 파싱
                    try:
                        parts = line.split()
                        if len(parts) >= 2:
                            line_num = abs(int(parts[1].split(',')[0]))
                    except Exception:
                        pass # 파싱 실패는 무시
                elif line.startswith('+') and not line.startswith('+++'):
                    result.added_count += 1
                    result.changes.append(DiffLine(
                        line_number=line_num,
                        change_type=ChangeType.ADDED,
                        new_text=line[1:].strip()
                    ))
                    line_num += 1
                elif line.startswith('-') and not line.startswith('---'):
                    result.deleted_count += 1
                    result.changes.append(DiffLine(
                        line_number=line_num,
                        change_type=ChangeType.DELETED,
                        original_text=line[1:].strip()
                    ))
                    line_num += 1
            
            return result
            
        except Exception as e:
            return DiffResult(
                success=False,
                file1_path=file1_path,
                file2_path=file2_path,
                error_message=str(e)
            )
    
    def compare_text(
        self,
        text1: str,
        text2: str
    ) -> DiffResult:
        """
        텍스트 직접 비교
        """
        lines1 = text1.split('\n')
        lines2 = text2.split('\n')
        
        result = DiffResult(
            success=True,
            file1_path="text1",
            file2_path="text2",
            file1_lines=len(lines1),
            file2_lines=len(lines2)
        )
        
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                for i in range(i1, i2):
                    result.modified_count += 1
                    result.changes.append(DiffLine(
                        line_number=i + 1,
                        change_type=ChangeType.MODIFIED,
                        original_text=lines1[i] if i < len(lines1) else "",
                        new_text=lines2[j1 + (i - i1)] if j1 + (i - i1) < len(lines2) else ""
                    ))
            elif tag == 'delete':
                for i in range(i1, i2):
                    result.deleted_count += 1
                    result.changes.append(DiffLine(
                        line_number=i + 1,
                        change_type=ChangeType.DELETED,
                        original_text=lines1[i]
                    ))
            elif tag == 'insert':
                for j in range(j1, j2):
                    result.added_count += 1
                    result.changes.append(DiffLine(
                        line_number=j + 1,
                        change_type=ChangeType.ADDED,
                        new_text=lines2[j]
                    ))
        
        return result
    
    def generate_report(
        self,
        result: DiffResult,
        output_path: str,
        format: str = "html"
    ) -> bool:
        """
        비교 리포트 생성
        
        Args:
            result: 비교 결과
            output_path: 출력 경로
            format: "html" 또는 "txt"
        
        Returns:
            성공 여부
        """
        from datetime import datetime
        
        report = DiffReport(
            title="문서 비교 리포트",
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            result=result
        )
        
        try:
            content = report.to_html() if format == "html" else report.to_text()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            self._logger.error(f"리포트 생성 오류: {e}")
            return False
