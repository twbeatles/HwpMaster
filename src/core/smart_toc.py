"""
Smart TOC Module
목차 생성기 - 글자 크기/굵기 분석으로 자동 목차 생성

Author: HWP Master
"""

import logging
import os
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from xml.etree import ElementTree


class HeadingLevel(Enum):
    """제목 수준"""
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    BODY = 0


@dataclass
class TocEntry:
    """목차 항목"""
    level: int
    text: str
    page: int = 0
    line_number: int = 0
    font_size: float = 0.0
    is_bold: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "text": self.text,
            "page": self.page,
            "line": self.line_number
        }
    
    @property
    def indent(self) -> str:
        return "  " * (self.level - 1)
    
    def format(self, include_page: bool = True) -> str:
        if include_page and self.page > 0:
            return f"{self.indent}{self.text} ..................... {self.page}"
        return f"{self.indent}{self.text}"


@dataclass
class TocResult:
    """목차 추출 결과"""
    success: bool
    file_path: str
    entries: list[TocEntry] = field(default_factory=list)
    error_message: Optional[str] = None
    analysis_mode: str = "pattern_only"
    
    @property
    def total_entries(self) -> int:
        return len(self.entries)
    
    def get_by_level(self, level: int) -> list[TocEntry]:
        return [e for e in self.entries if e.level == level]
    
    def to_text(self) -> str:
        """텍스트 형식 목차"""
        lines = ["=" * 40, "목 차", "=" * 40, ""]
        for entry in self.entries:
            lines.append(entry.format())
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """HTML 형식 목차"""
        html = """<div style="font-family: 'Malgun Gothic', sans-serif;">
<h2>목 차</h2>
<ul style="list-style: none; padding: 0;">
"""
        for entry in self.entries:
            indent = entry.level * 20
            html += f'<li style="margin-left: {indent}px; margin-bottom: 5px;">{entry.text}</li>\n'
        
        html += "</ul></div>"
        return html


class SmartTOC:
    """
    스마트 목차 생성기
    글자 크기와 굵기를 분석하여 자동으로 목차 생성
    """
    
    # 기본 제목 감지 규칙
    DEFAULT_RULES = {
        "h1_min_size": 16.0,  # pt
        "h2_min_size": 14.0,
        "h3_min_size": 12.0,
        "h4_min_size": 11.0,
        "bold_is_heading": True,
        "min_text_length": 2,
        "max_text_length": 100,
    }
    
    # 한국어 제목 패턴
    HEADING_PATTERNS = [
        r"^[1-9]\.",           # 1. 2. 3.
        r"^[一二三四五六七八九十]+\.",  # 한자 번호
        r"^[가나다라마바사]+\.",  # 가. 나. 다.
        r"^[①②③④⑤⑥⑦⑧⑨⑩]",  # 원문자
        r"^제\s*\d+\s*[조장절]",  # 제1조, 제2장
        r"^[IVX]+\.",          # 로마자
    ]
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._rules = self.DEFAULT_RULES.copy()
    
    def set_rules(self, rules: dict[str, Any]) -> None:
        """규칙 설정"""
        self._rules.update(rules)
    
    def extract_toc(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> TocResult:
        """
        목차 추출
        
        Args:
            file_path: HWP 파일 경로
            progress_callback: 진행률 콜백
        
        Returns:
            TocResult
        """
        entries: list[TocEntry] = []
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                # pyhwpx 호환 방식: 텍스트 직접 추출 후 패턴 분석
                # 전체 텍스트 추출
                hwp.Run("SelectAll")
                full_text = hwp.GetTextFile("TEXT", "")
                hwp.Run("Cancel")
                
                if not full_text:
                    return TocResult(
                        success=True,
                        file_path=file_path,
                        entries=[],
                        analysis_mode="pattern_only",
                    )

                page_lines = self._split_text_pages(full_text)
                style_hints, analysis_mode = self._extract_style_hints_from_hwpx(file_path)
                total_lines = len(page_lines)

                for idx, (line_number, page_number, line) in enumerate(page_lines, start=1):
                    line = line.strip()

                    if progress_callback and idx % 50 == 0:
                        progress_callback(idx, total_lines, "스캔 중...")

                    if not line or len(line) < self._rules["min_text_length"]:
                        continue

                    if len(line) > self._rules["max_text_length"]:
                        continue

                    font_size, is_bold = style_hints.get(line_number, (12.0, False))
                    level = self._determine_level(line, font_size, is_bold)

                    if level > 0:
                        entries.append(TocEntry(
                            level=level,
                            text=line,
                            line_number=line_number,
                            page=page_number,
                            font_size=float(font_size),
                            is_bold=bool(is_bold),
                        ))

                return TocResult(
                    success=True,
                    file_path=file_path,
                    entries=entries,
                    analysis_mode=analysis_mode,
                )
                
        except Exception as e:
            return TocResult(
                success=False,
                file_path=file_path,
                error_message=str(e),
                analysis_mode="pattern_only",
            )

    @staticmethod
    def _local_name(tag: str) -> str:
        if "}" in tag:
            return tag.rsplit("}", 1)[-1]
        return tag

    def _split_text_pages(self, full_text: str) -> list[tuple[int, int, str]]:
        normalized = str(full_text or "").replace("\r\n", "\n").replace("\r", "\n")
        page_blocks = normalized.split("\f")
        rows: list[tuple[int, int, str]] = []
        line_number = 0

        for page_number, block in enumerate(page_blocks, start=1):
            lines = block.split("\n")
            for line in lines:
                line_number += 1
                rows.append((line_number, page_number, line))

        return rows

    def _extract_style_hints_from_hwpx(self, file_path: str) -> tuple[dict[int, tuple[float, bool]], str]:
        """
        Best-effort style hint extraction from HWPX.
        Returns:
            ({line_number: (font_size, is_bold)}, analysis_mode)
        """
        hints: dict[int, tuple[float, bool]] = {}
        hwpx_path = Path(file_path)
        temp_hwpx: Optional[Path] = None

        try:
            if hwpx_path.suffix.lower() != ".hwpx":
                from .hwp_handler import HwpHandler

                with HwpHandler() as handler:
                    handler._ensure_hwp()
                    hwp = handler._hwp
                    hwp.open(file_path)
                    fd, tmp_name = tempfile.mkstemp(suffix=".hwpx")
                    os.close(fd)
                    Path(tmp_name).unlink(missing_ok=True)
                    temp_hwpx = Path(tmp_name)
                    hwp.save_as(str(temp_hwpx), format="HWPX")
                    hwpx_path = temp_hwpx

            if not hwpx_path.exists() or not zipfile.is_zipfile(hwpx_path):
                return {}, "pattern_only"

            with zipfile.ZipFile(hwpx_path, "r") as zf:
                style_ids: set[str] = set()
                header_name = "Contents/header.xml"
                if header_name in zf.namelist():
                    try:
                        root = ElementTree.fromstring(zf.read(header_name))
                        for elem in root.iter():
                            if self._local_name(elem.tag).lower() != "style":
                                continue
                            style_id = ""
                            style_name = ""
                            for key, value in elem.attrib.items():
                                lowered = key.lower()
                                if lowered.endswith("id") and not style_id:
                                    style_id = str(value)
                                if "name" in lowered:
                                    style_name = str(value)
                            lowered_name = style_name.lower()
                            if "heading" in lowered_name or "제목" in lowered_name:
                                if style_id:
                                    style_ids.add(style_id)
                    except Exception:
                        return {}, "pattern_only"

                if not style_ids:
                    return {}, "pattern_only"

                section_names = sorted(
                    [n for n in zf.namelist() if n.startswith("Contents/section") and n.endswith(".xml")]
                )
                line_idx = 0
                for name in section_names:
                    try:
                        section_root = ElementTree.fromstring(zf.read(name))
                    except Exception:
                        continue
                    for para in section_root.iter():
                        if self._local_name(para.tag).lower() != "p":
                            continue
                        line_idx += 1
                        style_ref = ""
                        for key, value in para.attrib.items():
                            lowered = key.lower()
                            if "styleidref" in lowered or ("style" in lowered and lowered.endswith("idref")):
                                style_ref = str(value)
                                break
                        if style_ref and style_ref in style_ids:
                            hints[line_idx] = (16.0, True)

            if hints:
                return hints, "pattern_plus_style_hint"
            return {}, "pattern_only"
        except Exception:
            return {}, "pattern_only"
        finally:
            if temp_hwpx is not None:
                try:
                    temp_hwpx.unlink(missing_ok=True)
                except Exception:
                    pass
    
    def _determine_level(
        self,
        text: str,
        font_size: float,
        is_bold: bool
    ) -> int:
        """
        제목 수준 결정
        
        Returns:
            0: 본문 (목차에 포함 안됨)
            1-4: 제목 수준
        """
        import re
        
        # 패턴 매칭
        for pattern in self.HEADING_PATTERNS:
            if re.match(pattern, text):
                # 패턴에 따른 수준 결정
                if re.match(r"^[1-9]\.", text) or re.match(r"^제\s*\d+\s*장", text):
                    return 1
                elif re.match(r"^[가나다라마바사]+\.", text) or re.match(r"^제\s*\d+\s*절", text):
                    return 2
                elif re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]", text):
                    return 3
                else:
                    return 2
        
        # 글자 크기 기반 결정
        if font_size >= self._rules["h1_min_size"]:
            return 1
        elif font_size >= self._rules["h2_min_size"]:
            return 2
        elif font_size >= self._rules["h3_min_size"] and is_bold:
            return 3
        elif is_bold and self._rules["bold_is_heading"]:
            return 4
        
        return 0  # 본문
    
    def extract_from_text(self, text: str) -> TocResult:
        """
        텍스트에서 목차 추출 (간단한 버전)
        """
        entries: list[TocEntry] = []

        for line_number, page_number, line in self._split_text_pages(text):
            line = line.strip()
            if not line:
                continue

            level = self._determine_level(line, 12.0, False)
            if level > 0:
                entries.append(TocEntry(
                    level=level,
                    text=line,
                    line_number=line_number,
                    page=page_number,
                ))

        return TocResult(
            success=True,
            file_path="text",
            entries=entries,
            analysis_mode="pattern_only",
        )
    
    def generate_toc_hwp(
        self,
        source_path: str,
        output_path: str,
        insert_at_beginning: bool = True
    ) -> bool:
        """
        목차를 HWP 문서에 삽입
        
        Args:
            source_path: 원본 파일 경로
            output_path: 출력 경로
            insert_at_beginning: 문서 시작에 삽입 여부
        
        Returns:
            성공 여부
        """
        try:
            result = self.extract_toc(source_path)
            if not result.success:
                return False
            
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(source_path)
                
                if insert_at_beginning:
                    # 문서 시작으로 이동 (pyhwpx 액션)
                    hwp.Run("MoveDocBegin")
                    
                    # 목차 제목 삽입 (pyhwpx 호환 방식)
                    hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
                    hwp.HParameterSet.HInsertText.Text = "목     차\r\n\r\n"
                    hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
                    
                    # 목차 항목 삽입 (pyhwpx 호환 방식)
                    for entry in result.entries:
                        toc_line = entry.format(include_page=False) + "\r\n"
                        hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
                        hwp.HParameterSet.HInsertText.Text = toc_line
                        hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
                    
                    # 페이지 나누기 (pyhwpx 액션)
                    hwp.Run("BreakPage")
                
                hwp.save_as(output_path)
                return True
                
        except Exception as e:
            self._logger.error(f"목차 삽입 오류: {e}")
            return False
    
    def save_toc_as_file(
        self,
        result: TocResult,
        output_path: str,
        format: str = "txt"
    ) -> bool:
        """
        목차를 파일로 저장
        """
        try:
            content = result.to_html() if format == "html" else result.to_text()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            self._logger.error(f"목차 파일 저장 실패: {e}")
            return False
