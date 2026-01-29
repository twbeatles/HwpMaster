"""
Smart TOC Module
목차 생성기 - 글자 크기/굵기 분석으로 자동 목차 생성

Author: HWP Master
"""

import logging
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


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
    
    def to_dict(self) -> dict:
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
    
    def set_rules(self, rules: dict) -> None:
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
                
                # 문단별 스캔
                ctrl = hwp.HeadCtrl
                line_number = 0
                current_page = 1
                
                while ctrl:
                    if ctrl.CtrlID == "secd":
                        para = ctrl.FirstParaHeadCtrl
                        while para:
                            line_number += 1
                            
                            if progress_callback:
                                progress_callback(line_number, line_number * 2, "스캔 중...")
                            
                            try:
                                # 텍스트 추출
                                text = para.String.strip() if para.String else ""
                                
                                if not text or len(text) < self._rules["min_text_length"]:
                                    para = para.NextParaHeadCtrl
                                    continue
                                
                                if len(text) > self._rules["max_text_length"]:
                                    para = para.NextParaHeadCtrl
                                    continue
                                
                                # 글자 속성 분석
                                font_size = 10.0
                                is_bold = False
                                
                                try:
                                    char_shape = para.CharShape
                                    if char_shape:
                                        font_size = char_shape.Height / 100
                                        is_bold = char_shape.Bold
                                except Exception as e:
                                    self._logger.debug(f"글자 속성 분석 실패 (줄 {line_number}): {e}")
                                
                                # 제목 수준 결정
                                level = self._determine_level(text, font_size, is_bold)
                                
                                if level > 0:
                                    entries.append(TocEntry(
                                        level=level,
                                        text=text,
                                        page=current_page,
                                        line_number=line_number,
                                        font_size=font_size,
                                        is_bold=is_bold
                                    ))
                                    
                            except Exception as e:
                                self._logger.debug(f"목차 항목 처리 중 오류 (줄 {line_number}): {e}")
                            
                            para = para.NextParaHeadCtrl
                    
                    ctrl = ctrl.NextCtrl
                
                return TocResult(
                    success=True,
                    file_path=file_path,
                    entries=entries
                )
                
        except Exception as e:
            return TocResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )
    
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
        import re
        
        entries: list[TocEntry] = []
        
        for i, line in enumerate(text.split('\n')):
            line = line.strip()
            if not line:
                continue
            
            level = 0
            for pattern in self.HEADING_PATTERNS:
                if re.match(pattern, line):
                    if re.match(r"^[1-9]\.", line):
                        level = 1
                    elif re.match(r"^[가나다라마바사]+\.", line):
                        level = 2
                    elif re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]", line):
                        level = 3
                    else:
                        level = 2
                    break
            
            if level > 0:
                entries.append(TocEntry(
                    level=level,
                    text=line,
                    line_number=i + 1
                ))
        
        return TocResult(
            success=True,
            file_path="text",
            entries=entries
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
                    # 문서 시작으로 이동
                    hwp.MovePos(2)  # 문서 처음
                    
                    # 목차 제목 삽입
                    hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
                    hwp.HParameterSet.HInsertText.Text = "목     차\r\n\r\n"
                    hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
                    
                    # 목차 항목 삽입
                    for entry in result.entries:
                        toc_line = entry.format(include_page=False) + "\r\n"
                        hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
                        hwp.HParameterSet.HInsertText.Text = toc_line
                        hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
                    
                    # 페이지 나누기
                    hwp.HAction.Run("BreakPage")
                
                hwp.SaveAs(output_path)
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
