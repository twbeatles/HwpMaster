"""
Style Cop Module
서식 경찰 - 폰트, 크기, 줄간격 일괄 통일

Author: HWP Master
"""

import logging

from typing import Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum


class StylePreset(Enum):
    """스타일 프리셋"""
    OFFICIAL_DOCUMENT = "공문서 표준"
    REPORT = "보고서"
    THESIS = "논문"
    PROPOSAL = "제안서"
    CUSTOM = "사용자 정의"


@dataclass
class StyleRule:
    """스타일 규칙"""
    name: str
    font_name: str = "맑은 고딕"
    font_size: float = 11.0  # pt
    line_spacing: float = 160.0  # %
    paragraph_spacing_before: float = 0.0  # pt
    paragraph_spacing_after: float = 0.0  # pt
    first_line_indent: float = 10.0  # pt (첫 줄 들여쓰기)
    apply_to_body: bool = True
    apply_to_heading: bool = False
    heading_font_name: Optional[str] = None
    heading_font_size: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleRule":
        return cls(**data)


@dataclass
class StyleCheckResult:
    """스타일 검사 결과"""
    file_path: str
    total_paragraphs: int = 0
    inconsistent_fonts: int = 0
    inconsistent_sizes: int = 0
    inconsistent_spacing: int = 0
    issues: list[str] = field(default_factory=list)
    
    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0
    
    @property
    def compliance_score(self) -> float:
        if self.total_paragraphs == 0:
            return 100.0
        total_issues = self.inconsistent_fonts + self.inconsistent_sizes + self.inconsistent_spacing
        return max(0, 100 - (total_issues / self.total_paragraphs * 100))


@dataclass
class StyleApplyResult:
    """스타일 적용 결과"""
    success: bool
    file_path: str
    paragraphs_modified: int = 0
    error_message: Optional[str] = None


class StyleCop:
    """
    서식 경찰
    문서 스타일 검사 및 일괄 적용
    """
    
    # 프리셋 정의
    PRESETS: dict[str, StyleRule] = {
        "official": StyleRule(
            name="공문서 표준",
            font_name="맑은 고딕",
            font_size=11.0,
            line_spacing=160.0,
            first_line_indent=10.0
        ),
        "report": StyleRule(
            name="보고서",
            font_name="맑은 고딕",
            font_size=11.0,
            line_spacing=180.0,
            first_line_indent=0.0
        ),
        "thesis": StyleRule(
            name="논문",
            font_name="바탕",
            font_size=10.0,
            line_spacing=200.0,
            first_line_indent=10.0
        ),
        "proposal": StyleRule(
            name="제안서",
            font_name="맑은 고딕",
            font_size=11.0,
            line_spacing=150.0,
            first_line_indent=0.0
        ),
    }
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._custom_rules: list[StyleRule] = []
    
    def get_presets(self) -> list[StyleRule]:
        """프리셋 목록"""
        return list(self.PRESETS.values())
    
    def get_preset(self, preset_id: str) -> Optional[StyleRule]:
        """프리셋 조회"""
        return self.PRESETS.get(preset_id)
    
    def check_style(
        self,
        file_path: str,
        rule: StyleRule
    ) -> StyleCheckResult:
        """
        스타일 검사
        
        Args:
            file_path: HWP 파일 경로
            rule: 적용할 스타일 규칙
        
        Returns:
            StyleCheckResult
        """
        result = StyleCheckResult(file_path=file_path)
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                # 문단별 스타일 검사
                ctrl = hwp.HeadCtrl
                para_count = 0
                
                while ctrl:
                    if ctrl.CtrlID == "secd":  # 섹션
                        para = ctrl.FirstParaHeadCtrl
                        while para:
                            para_count += 1
                            
                            # 폰트 검사
                            try:
                                char_shape = para.CharShape
                                if char_shape:
                                    face_name = char_shape.FaceName
                                    font_size = char_shape.Height / 100  # 포인트로 변환
                                    
                                    if face_name and face_name != rule.font_name:
                                        result.inconsistent_fonts += 1
                                        result.issues.append(f"폰트 불일치: {face_name} (기준: {rule.font_name})")
                                    
                                    if abs(font_size - rule.font_size) > 0.5:
                                        result.inconsistent_sizes += 1
                                        result.issues.append(f"크기 불일치: {font_size}pt (기준: {rule.font_size}pt)")
                            except Exception as e:
                                self._logger.warning(f"폰트 검사 중 오류: {e}")
                            
                            # 줄간격 검사
                            try:
                                para_shape = para.ParaShape
                                if para_shape:
                                    line_spacing = para_shape.LineSpacing
                                    if abs(line_spacing - rule.line_spacing) > 5:
                                        result.inconsistent_spacing += 1
                                        result.issues.append(f"줄간격 불일치: {line_spacing}% (기준: {rule.line_spacing}%)")
                            except Exception as e:
                                self._logger.warning(f"줄간격 검사 중 오류: {e}")
                            
                            para = para.NextParaHeadCtrl
                    
                    ctrl = ctrl.NextCtrl
                
                result.total_paragraphs = para_count
                
        except Exception as e:
            result.issues.append(f"검사 오류: {e}")
        
        return result
    
    def apply_style(
        self,
        file_path: str,
        rule: StyleRule,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> StyleApplyResult:
        """
        스타일 적용
        
        Args:
            file_path: HWP 파일 경로
            rule: 적용할 스타일 규칙
            output_path: 출력 경로 (None이면 원본 덮어쓰기)
            progress_callback: 진행률 콜백
        
        Returns:
            StyleApplyResult
        """
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                # 전체 선택 (pyhwpx 액션 사용)
                hwp.Run("SelectAll")
                
                # 문자 서식 설정
                hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet)
                
                char_shape = hwp.HParameterSet.HCharShape
                char_shape.FaceNameHangul = rule.font_name
                char_shape.FaceNameLatin = rule.font_name
                char_shape.Height = hwp.PointToHwpUnit(rule.font_size)
                
                hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)
                
                # 문단 서식 설정
                hwp.HAction.GetDefault("ParaShape", hwp.HParameterSet.HParaShape.HSet)
                
                para_shape = hwp.HParameterSet.HParaShape
                para_shape.LineSpacingType = 0  # 퍼센트
                para_shape.LineSpacing = int(rule.line_spacing)
                
                if rule.first_line_indent > 0:
                    para_shape.FirstLineIndent = hwp.PointToHwpUnit(rule.first_line_indent)
                
                hwp.HAction.Execute("ParaShape", hwp.HParameterSet.HParaShape.HSet)
                
                # 선택 해제 (pyhwpx 액션 사용)
                hwp.Run("Cancel")
                
                # 저장 (pyhwpx 메서드 사용)
                save_path = output_path if output_path else file_path
                hwp.save_as(save_path)
                
                return StyleApplyResult(
                    success=True,
                    file_path=save_path,
                    paragraphs_modified=1  # 전체 적용
                )
                
        except Exception as e:
            return StyleApplyResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )
    
    def batch_apply_style(
        self,
        files: list[str],
        rule: StyleRule,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[StyleApplyResult]:
        """
        일괄 스타일 적용
        
        Args:
            files: 파일 경로 목록
            rule: 적용할 스타일 규칙
            output_dir: 출력 디렉토리
            progress_callback: 진행률 콜백
        
        Returns:
            StyleApplyResult 목록
        """
        from pathlib import Path
        
        results: list[StyleApplyResult] = []
        total = len(files)
        
        for idx, file_path in enumerate(files, start=1):
            filename = Path(file_path).name
            
            if progress_callback:
                progress_callback(idx, total, filename)
            
            if output_dir:
                output_path = str(Path(output_dir) / filename)
            else:
                output_path = None
            
            result = self.apply_style(file_path, rule, output_path)
            results.append(result)
        
        return results
    
    def create_custom_rule(
        self,
        name: str,
        font_name: str = "맑은 고딕",
        font_size: float = 11.0,
        line_spacing: float = 160.0,
        first_line_indent: float = 10.0
    ) -> StyleRule:
        """커스텀 규칙 생성"""
        rule = StyleRule(
            name=name,
            font_name=font_name,
            font_size=font_size,
            line_spacing=line_spacing,
            first_line_indent=first_line_indent
        )
        self._custom_rules.append(rule)
        return rule
