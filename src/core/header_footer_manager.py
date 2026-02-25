"""
Header/Footer Manager Module
HWP 문서 헤더/푸터 관리

Author: HWP Master
"""

import gc
import logging
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .hwp_handler import HwpHandler


class PageNumberFormat(Enum):
    """페이지 번호 형식"""
    SIMPLE = "simple"           # 1, 2, 3
    TOTAL = "total"             # 1/10, 2/10
    DASH = "dash"               # -1-, -2-
    BRACKET = "bracket"         # [1], [2]
    KOREAN = "korean"           # 1쪽, 2쪽


class HeaderFooterPosition(Enum):
    """헤더/푸터 정렬"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class HeaderFooterConfig:
    """헤더/푸터 설정"""
    # 헤더 설정
    header_enabled: bool = False
    header_left: str = ""
    header_center: str = ""
    header_right: str = ""
    
    # 푸터 설정
    footer_enabled: bool = True
    footer_left: str = ""
    footer_center: str = ""
    footer_right: str = ""
    
    # 페이지 번호
    page_number_enabled: bool = True
    page_number_format: PageNumberFormat = PageNumberFormat.SIMPLE
    page_number_position: HeaderFooterPosition = HeaderFooterPosition.CENTER
    page_number_in_footer: bool = True  # True: 푸터, False: 헤더
    
    # 스타일
    font_name: str = "맑은 고딕"
    font_size: int = 10
    
    # 특수 변수
    include_date: bool = False
    include_filename: bool = False


@dataclass
class HeaderFooterResult:
    """헤더/푸터 적용 결과"""
    success: bool
    source_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


# 프리셋
HEADER_FOOTER_PRESETS: dict[str, HeaderFooterConfig] = {
    "공문서 스타일": HeaderFooterConfig(
        header_enabled=False,
        footer_enabled=True,
        page_number_enabled=True,
        page_number_format=PageNumberFormat.DASH,
        page_number_position=HeaderFooterPosition.CENTER,
        font_name="맑은 고딕",
        font_size=10
    ),
    "보고서 스타일": HeaderFooterConfig(
        header_enabled=True,
        header_right="{{filename}}",
        footer_enabled=True,
        page_number_enabled=True,
        page_number_format=PageNumberFormat.TOTAL,
        page_number_position=HeaderFooterPosition.RIGHT,
        include_filename=True,
        font_name="맑은 고딕",
        font_size=9
    ),
    "논문 스타일": HeaderFooterConfig(
        header_enabled=True,
        header_center="{{title}}",
        footer_enabled=True,
        page_number_enabled=True,
        page_number_format=PageNumberFormat.SIMPLE,
        page_number_position=HeaderFooterPosition.CENTER,
        font_name="바탕",
        font_size=10
    ),
    "제안서 스타일": HeaderFooterConfig(
        header_enabled=True,
        header_left="{{company}}",
        header_right="{{date}}",
        footer_enabled=True,
        page_number_enabled=True,
        page_number_format=PageNumberFormat.TOTAL,
        page_number_position=HeaderFooterPosition.RIGHT,
        include_date=True,
        font_name="맑은 고딕",
        font_size=9
    ),
}


class HeaderFooterManager:
    """
    헤더/푸터 관리자
    HWP 문서의 헤더/푸터 일괄 설정
    """
    
    def __init__(self) -> None:
        self._handler: Optional["HwpHandler"] = None
        self._logger = logging.getLogger(__name__)
        self._owner_thread_id: Optional[int] = None

    def _ensure_hwp(self) -> None:
        """HWP 핸들러 초기화 보장"""
        self._get_hwp()

    @property
    def _hwp(self) -> Any:
        """초기화된 내부 HWP 객체"""
        return self._get_hwp()
    
    def _get_hwp(self) -> Any:
        """HwpHandler를 통해 HWP 인스턴스 반환"""
        import threading

        tid = threading.get_ident()
        if self._handler is not None and self._owner_thread_id is not None and self._owner_thread_id != tid:
            raise RuntimeError("HeaderFooterManager는 스레드 안전하지 않습니다. Worker마다 새 인스턴스를 생성하세요.")

        if self._handler is None:
            from .hwp_handler import HwpHandler
            handler = HwpHandler()
            handler._ensure_hwp()
            self._handler = handler
            self._owner_thread_id = tid

        handler = self._handler
        if handler is None:
            raise RuntimeError("HWP 핸들러 초기화 실패")

        hwp = handler._hwp
        if hwp is None:
            raise RuntimeError("HWP 인스턴스 초기화 실패")
        return hwp
    
    def close(self) -> None:
        """한글 인스턴스 종료"""
        if self._handler is not None:
            try:
                self._handler.close()
            except Exception as e:
                self._logger.warning(f"HWP 종료 중 오류 (무시됨): {e}")
            finally:
                self._handler = None
                self._owner_thread_id = None
                gc.collect()
    
    def __enter__(self):
        self._get_hwp()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    @staticmethod
    def get_presets() -> dict[str, HeaderFooterConfig]:
        """프리셋 목록 반환"""
        return HEADER_FOOTER_PRESETS.copy()
    
    def _format_page_number(self, format_type: PageNumberFormat) -> str:
        """페이지 번호 형식 문자열 반환"""
        formats = {
            PageNumberFormat.SIMPLE: "{{page}}",
            PageNumberFormat.TOTAL: "{{page}}/{{total}}",
            PageNumberFormat.DASH: "- {{page}} -",
            PageNumberFormat.BRACKET: "[{{page}}]",
            PageNumberFormat.KOREAN: "{{page}}쪽",
        }
        return formats.get(format_type, "{{page}}")

    def _replace_variables(self, text: str, source_path: str) -> str:
        """변수를 실제 값으로 치환"""
        result = text
        
        # 파일명 치환
        if "{{filename}}" in result:
            result = result.replace("{{filename}}", Path(source_path).stem)
        
        # 날짜 치환
        if "{{date}}" in result:
            result = result.replace("{{date}}", datetime.now().strftime("%Y-%m-%d"))
        
        # 제목 (파일명 기반)
        if "{{title}}" in result:
            result = result.replace("{{title}}", Path(source_path).stem)
        
        # 회사명 (기본값)
        if "{{company}}" in result:
            result = result.replace("{{company}}", "")
        
        return result

    def _apply_text_style(self, config: HeaderFooterConfig) -> None:
        """헤더/푸터 텍스트 스타일 적용."""
        try:
            self._hwp.HAction.GetDefault("CharShape", self._hwp.HParameterSet.HCharShape.HSet)
            char_shape = self._hwp.HParameterSet.HCharShape
            char_shape.FaceNameHangul = config.font_name
            char_shape.FaceNameLatin = config.font_name
            char_shape.Height = self._hwp.PointToHwpUnit(float(config.font_size))
            self._hwp.HAction.Execute("CharShape", self._hwp.HParameterSet.HCharShape.HSet)
        except Exception as e:
            self._logger.debug(f"헤더/푸터 글꼴 적용 실패(무시): {e}")
    
    def apply_header_footer(
        self,
        source_path: str,
        config: HeaderFooterConfig,
        output_path: Optional[str] = None
    ) -> HeaderFooterResult:
        """
        헤더/푸터 적용
        
        Args:
            source_path: 원본 파일 경로
            config: 헤더/푸터 설정
            output_path: 출력 경로 (None이면 덮어쓰기)
        
        Returns:
            적용 결과
        """
        try:
            self._ensure_hwp()
            
            source = Path(source_path)
            if not source.exists():
                return HeaderFooterResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"파일이 존재하지 않습니다: {source_path}"
                )
            
            # 파일 열기
            self._hwp.open(source_path)
            
            # 기존 헤더/푸터 삭제
            self._clear_header_footer()
            
            # 헤더 설정
            if config.header_enabled:
                self._set_header(config, source_path)
            
            # 푸터 설정
            if config.footer_enabled:
                self._set_footer(config, source_path)
            
            # 페이지 번호 설정
            if config.page_number_enabled:
                self._set_page_number(config)
            
            # 저장
            save_path = output_path if output_path else source_path
            self._hwp.save_as(save_path)
            
            return HeaderFooterResult(
                success=True,
                source_path=source_path,
                output_path=save_path
            )
            
        except Exception as e:
            return HeaderFooterResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )
    
    def _clear_header_footer(self) -> None:
        """기존 헤더/푸터 삭제"""
        try:
            # 머리말 삭제
            self._hwp.HAction.Run("DeleteHeader")
        except Exception as e:
            self._logger.warning(f"머리말 삭제 중 오류: {e}")
        
        try:
            # 꼬리말 삭제
            self._hwp.HAction.Run("DeleteFooter")
        except Exception as e:
            self._logger.warning(f"꼬리말 삭제 중 오류: {e}")
    
    def _set_header(self, config: HeaderFooterConfig, source_path: str) -> None:
        """헤더 설정"""
        try:
            self._hwp.HAction.Run("HeaderFooterMode")
            
            # 헤더 영역으로 이동
            pset = self._hwp.HParameterSet.HHeaderFooter
            self._hwp.HAction.GetDefault("InsertHeader", pset.HSet)
            pset.HeaderType = 0  # 양쪽
            self._hwp.HAction.Execute("InsertHeader", pset.HSet)
            
            # 텍스트 삽입
            header_text = ""
            if config.header_left:
                header_text += self._replace_variables(config.header_left, source_path)
            if config.header_center:
                header_text += "\t" + self._replace_variables(config.header_center, source_path)
            if config.header_right:
                header_text += "\t" + self._replace_variables(config.header_right, source_path)

            if config.include_filename and "{{filename}}" not in header_text:
                header_text += "\t" + Path(source_path).name
            if config.include_date and "{{date}}" not in header_text:
                header_text += "\t" + datetime.now().strftime("%Y-%m-%d")
            
            if header_text:
                # pyhwpx 호환 방식으로 텍스트 삽입
                self._hwp.HAction.GetDefault("InsertText", self._hwp.HParameterSet.HInsertText.HSet)
                self._hwp.HParameterSet.HInsertText.Text = header_text.strip()
                self._hwp.HAction.Execute("InsertText", self._hwp.HParameterSet.HInsertText.HSet)
                self._apply_text_style(config)
            
            self._hwp.HAction.Run("CloseHeaderFooter")
            
        except Exception as e:
            self._logger.warning(f"헤더 설정 실패: {e}")
    
    def _set_footer(self, config: HeaderFooterConfig, source_path: str) -> None:
        """푸터 설정"""
        try:
            self._hwp.HAction.Run("HeaderFooterMode")
            
            # 푸터 영역으로 이동
            pset = self._hwp.HParameterSet.HHeaderFooter
            self._hwp.HAction.GetDefault("InsertFooter", pset.HSet)
            pset.FooterType = 0  # 양쪽
            self._hwp.HAction.Execute("InsertFooter", pset.HSet)
            
            # 텍스트 삽입
            footer_text = ""
            if config.footer_left:
                footer_text += self._replace_variables(config.footer_left, source_path)
            if config.footer_center:
                footer_text += "\t" + self._replace_variables(config.footer_center, source_path)
            if config.footer_right:
                footer_text += "\t" + self._replace_variables(config.footer_right, source_path)

            if config.include_filename and "{{filename}}" not in footer_text:
                footer_text += "\t" + Path(source_path).name
            if config.include_date and "{{date}}" not in footer_text:
                footer_text += "\t" + datetime.now().strftime("%Y-%m-%d")
            
            if footer_text:
                # pyhwpx 호환 방식으로 텍스트 삽입
                self._hwp.HAction.GetDefault("InsertText", self._hwp.HParameterSet.HInsertText.HSet)
                self._hwp.HParameterSet.HInsertText.Text = footer_text.strip()
                self._hwp.HAction.Execute("InsertText", self._hwp.HParameterSet.HInsertText.HSet)
                self._apply_text_style(config)
            
            self._hwp.HAction.Run("CloseHeaderFooter")
            
        except Exception as e:
            self._logger.warning(f"푸터 설정 실패: {e}")
    
    def _set_page_number(self, config: HeaderFooterConfig) -> None:
        """페이지 번호 설정"""
        try:
            self._hwp.HAction.Run("InsertPageNum")
            
            pset = self._hwp.HParameterSet.HAutoNum
            self._hwp.HAction.GetDefault("InsertPageNum", pset.HSet)
            
            # 위치 설정
            position_map = {
                HeaderFooterPosition.LEFT: 0,
                HeaderFooterPosition.CENTER: 1,
                HeaderFooterPosition.RIGHT: 2,
            }
            pset.Position = position_map.get(config.page_number_position, 1)
            
            # 헤더/푸터 선택
            pset.InHeader = not config.page_number_in_footer
            
            # 형식 설정
            format_map = {
                PageNumberFormat.SIMPLE: 0,
                PageNumberFormat.TOTAL: 1,
                PageNumberFormat.DASH: 2,
                PageNumberFormat.BRACKET: 3,
                PageNumberFormat.KOREAN: 4,
            }
            pset.FormatType = format_map.get(config.page_number_format, 0)
            
            self._hwp.HAction.Execute("InsertPageNum", pset.HSet)
            
        except Exception as e:
            self._logger.warning(f"페이지 번호 설정 실패: {e}")
    
    def batch_apply_header_footer(
        self,
        source_files: list[str],
        config: HeaderFooterConfig,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[HeaderFooterResult]:
        """
        일괄 헤더/푸터 적용
        """
        results: list[HeaderFooterResult] = []
        total = len(source_files)
        
        try:
            self._ensure_hwp()
            
            for idx, source_path in enumerate(source_files):
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                if output_dir:
                    from ..utils.output_paths import resolve_output_path

                    output_path = resolve_output_path(output_dir, source_path)
                else:
                    output_path = None
                
                result = self.apply_header_footer(source_path, config, output_path)
                results.append(result)
                
                if (idx + 1) % 50 == 0:
                    gc.collect()
                    
        except Exception as e:
            for remaining in source_files[len(results):]:
                results.append(HeaderFooterResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results
    
    def remove_header_footer(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        remove_header: bool = True,
        remove_footer: bool = True
    ) -> HeaderFooterResult:
        """헤더/푸터 제거"""
        try:
            self._ensure_hwp()
            
            self._hwp.open(source_path)
            
            if remove_header:
                try:
                    self._hwp.HAction.Run("DeleteHeader")
                except Exception as e:
                    self._logger.warning(f"헤더 삭제 중 오류: {e}")
            
            if remove_footer:
                try:
                    self._hwp.HAction.Run("DeleteFooter")
                except Exception as e:
                    self._logger.warning(f"푸터 삭제 중 오류: {e}")
            
            save_path = output_path if output_path else source_path
            self._hwp.save_as(save_path)
            
            return HeaderFooterResult(
                success=True,
                source_path=source_path,
                output_path=save_path
            )
            
        except Exception as e:
            return HeaderFooterResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )
