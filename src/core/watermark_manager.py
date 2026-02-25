"""
Watermark Manager Module
HWP 문서에 워터마크 삽입

Author: HWP Master
"""

import os
import gc
import logging
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING, Any
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from .hwp_handler import HwpHandler


class WatermarkType(Enum):
    """워터마크 타입"""
    TEXT = "text"
    IMAGE = "image"


class WatermarkPosition(Enum):
    """워터마크 위치"""
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    DIAGONAL = "diagonal"


@dataclass
class WatermarkConfig:
    """워터마크 설정"""
    watermark_type: WatermarkType = WatermarkType.TEXT
    text: str = "대외비"
    font_name: str = "맑은 고딕"
    font_size: int = 48
    opacity: int = 30  # 0-100
    rotation: int = -45  # 각도 (-180 ~ 180)
    position: WatermarkPosition = WatermarkPosition.DIAGONAL
    color: str = "#888888"
    image_path: Optional[str] = None


@dataclass
class WatermarkResult:
    """워터마크 적용 결과"""
    success: bool
    source_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


# 프리셋 워터마크
WATERMARK_PRESETS: dict[str, WatermarkConfig] = {
    "대외비": WatermarkConfig(
        text="대외비",
        font_size=60,
        opacity=25,
        rotation=-45,
        color="#ff0000"
    ),
    "DRAFT": WatermarkConfig(
        text="DRAFT",
        font_size=72,
        opacity=20,
        rotation=-30,
        color="#888888"
    ),
    "CONFIDENTIAL": WatermarkConfig(
        text="CONFIDENTIAL",
        font_size=48,
        opacity=25,
        rotation=-45,
        color="#cc0000"
    ),
    "SAMPLE": WatermarkConfig(
        text="SAMPLE",
        font_size=60,
        opacity=30,
        rotation=-45,
        color="#0066cc"
    ),
    "사본": WatermarkConfig(
        text="사본",
        font_size=72,
        opacity=25,
        rotation=-45,
        color="#666666"
    ),
    "무단복제금지": WatermarkConfig(
        text="무단복제금지",
        font_size=42,
        opacity=20,
        rotation=-30,
        color="#990000"
    ),
}


class WatermarkManager:
    """
    워터마크 관리자
    HWP 문서에 텍스트/이미지 워터마크 삽입
    """
    
    def __init__(self) -> None:
        self._handler: Optional["HwpHandler"] = None
        self._logger = logging.getLogger(__name__)
        self._owner_thread_id: Optional[int] = None
    
    def _ensure_hwp(self) -> "HwpHandler":
        """HwpHandler 인스턴스 초기화 및 반환"""
        import threading

        tid = threading.get_ident()
        if self._handler is not None and self._owner_thread_id is not None and self._owner_thread_id != tid:
            raise RuntimeError("WatermarkManager는 스레드 안전하지 않습니다. Worker마다 새 인스턴스를 생성하세요.")

        if self._handler is None:
            from .hwp_handler import HwpHandler
            handler = HwpHandler()
            handler._ensure_hwp()
            self._handler = handler
            self._owner_thread_id = tid
        handler = self._handler
        if handler is None:
            raise RuntimeError("HWP 핸들러 초기화 실패")
        return handler
    
    def _get_hwp(self) -> Any:
        """내부 hwp 객체 반환"""
        handler = self._ensure_hwp()
        return handler._hwp
    
    def close(self) -> None:
        """핸들러 종료"""
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
        self._ensure_hwp()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    @staticmethod
    def get_presets() -> dict[str, WatermarkConfig]:
        """프리셋 목록 반환"""
        return WATERMARK_PRESETS.copy()

    @staticmethod
    def _hex_to_rgb(color: str) -> tuple[int, int, int]:
        text = str(color or "").strip().lstrip("#")
        if len(text) == 3:
            text = "".join(ch * 2 for ch in text)
        if len(text) != 6:
            return (128, 128, 128)
        try:
            return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        except Exception:
            return (128, 128, 128)

    @staticmethod
    def _set_attr_if_exists(target: Any, name: str, value: Any) -> bool:
        if hasattr(target, name):
            setattr(target, name, value)
            return True
        return False
    
    def apply_watermark(
        self,
        source_path: str,
        config: WatermarkConfig,
        output_path: Optional[str] = None
    ) -> WatermarkResult:
        """
        단일 문서에 워터마크 적용
        
        Args:
            source_path: 원본 파일 경로
            config: 워터마크 설정
            output_path: 출력 경로 (None이면 덮어쓰기)
        
        Returns:
            워터마크 적용 결과
        """
        try:
            hwp = self._get_hwp()
            
            source = Path(source_path)
            if not source.exists():
                return WatermarkResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"파일이 존재하지 않습니다: {source_path}"
                )
            
            # 파일 열기
            hwp.open(source_path)
            
            # 워터마크 삽입
            if config.watermark_type == WatermarkType.TEXT:
                self._insert_text_watermark(config)
            else:
                self._insert_image_watermark(config)
            
            # 저장
            save_path = output_path if output_path else source_path
            hwp.save_as(save_path)
            
            return WatermarkResult(
                success=True,
                source_path=source_path,
                output_path=save_path
            )
            
        except Exception as e:
            return WatermarkResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )
    
    def _insert_text_watermark(self, config: WatermarkConfig) -> None:
        """텍스트 워터마크 삽입"""
        hwp = self._get_hwp()
        try:
            # 머리말 영역에 텍스트 박스로 워터마크 삽입
            # pyhwpx API를 사용하여 워터마크 효과 구현
            
            # 워터마크 텍스트 설정
            watermark_text = config.text
            
            # 글자 격침 방식으로 워터마크 삽입 (배경으로)
            # HAction을 통해 워터마크 삽입
            hwp.HAction.Run("InsertWatermark")
            
            # 워터마크 속성 설정
            pset = hwp.HParameterSet.HWatermarkType
            hwp.HAction.GetDefault("InsertWatermark", pset.HSet)
            
            pset.Type = 0  # 텍스트
            self._set_attr_if_exists(pset, "Text", watermark_text)
            self._set_attr_if_exists(pset, "FontName", config.font_name)
            self._set_attr_if_exists(pset, "FontSize", int(config.font_size))
            self._set_attr_if_exists(pset, "Angle", int(config.rotation))
            self._set_attr_if_exists(pset, "Transparency", 100 - int(config.opacity))

            r, g, b = self._hex_to_rgb(config.color)
            color_value = None
            try:
                color_value = hwp.RGBColor(r, g, b)
            except Exception:
                color_value = None
            if color_value is not None:
                self._set_attr_if_exists(pset, "TextColor", color_value)
                self._set_attr_if_exists(pset, "Color", color_value)

            position_map = {
                WatermarkPosition.CENTER: 0,
                WatermarkPosition.TOP_LEFT: 1,
                WatermarkPosition.TOP_RIGHT: 2,
                WatermarkPosition.BOTTOM_LEFT: 3,
                WatermarkPosition.BOTTOM_RIGHT: 4,
                WatermarkPosition.DIAGONAL: 5,
            }
            pos = position_map.get(config.position, 5)
            self._set_attr_if_exists(pset, "Position", pos)
            self._set_attr_if_exists(pset, "PosType", pos)
            
            hwp.HAction.Execute("InsertWatermark", pset.HSet)
            
        except Exception as e:
            self._logger.warning(f"워터마크 삽입 대체 방법 시도: {e}")
            # 대체 방법: 머리말에 텍스트 삽입
            self._insert_watermark_fallback(config)
    
    def _insert_watermark_fallback(self, config: WatermarkConfig) -> None:
        """워터마크 삽입 대체 방법"""
        hwp = self._get_hwp()
        try:
            # 모든 페이지에 적용되도록 머리말 영역 사용
            hwp.HAction.Run("HeaderFooterMode")
            
            # 텍스트 박스 삽입
            pset = hwp.HParameterSet.HShapeObject
            hwp.HAction.GetDefault("DrawTextBox", pset.HSet)
            
            # 텍스트 박스 위치 및 크기 설정 (중앙 대각선)
            pset.Width = hwp.MiliToHwpUnit(200)
            pset.Height = hwp.MiliToHwpUnit(100)
            pset.TextWrap = 2  # 글자 앞으로
            pset.TreatAsChar = 0
            
            hwp.HAction.Execute("DrawTextBox", pset.HSet)
            
            # 텍스트 입력
            hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
            hwp.HParameterSet.HInsertText.Text = config.text
            hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)

            # 폰트/크기/색상 반영 (지원되는 환경에서만 적용)
            try:
                hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet)
                hwp.HParameterSet.HCharShape.FaceNameHangul = config.font_name
                hwp.HParameterSet.HCharShape.FaceNameLatin = config.font_name
                hwp.HParameterSet.HCharShape.Height = hwp.PointToHwpUnit(float(config.font_size))
                r, g, b = self._hex_to_rgb(config.color)
                hwp.HParameterSet.HCharShape.TextColor = hwp.RGBColor(r, g, b)
                hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)
            except Exception as style_e:
                self._logger.debug(f"대체 워터마크 문자 스타일 적용 실패(무시): {style_e}")

            hwp.HAction.Run("Cancel")
            
        except Exception as e:
            self._logger.error(f"워터마크 삽입 실패: {e}")
    
    def _insert_image_watermark(self, config: WatermarkConfig) -> None:
        """이미지 워터마크 삽입"""
        if not config.image_path or not os.path.exists(config.image_path):
            raise ValueError("이미지 경로가 유효하지 않습니다.")
        
        hwp = self._get_hwp()
        try:
            hwp.HAction.Run("InsertWatermark")
            
            pset = hwp.HParameterSet.HWatermarkType
            hwp.HAction.GetDefault("InsertWatermark", pset.HSet)
            
            pset.Type = 1  # 이미지
            self._set_attr_if_exists(pset, "ImagePath", config.image_path)
            self._set_attr_if_exists(pset, "Transparency", 100 - int(config.opacity))

            position_map = {
                WatermarkPosition.CENTER: 0,
                WatermarkPosition.TOP_LEFT: 1,
                WatermarkPosition.TOP_RIGHT: 2,
                WatermarkPosition.BOTTOM_LEFT: 3,
                WatermarkPosition.BOTTOM_RIGHT: 4,
                WatermarkPosition.DIAGONAL: 5,
            }
            pos = position_map.get(config.position, 0)
            self._set_attr_if_exists(pset, "Position", pos)
            self._set_attr_if_exists(pset, "PosType", pos)
            
            hwp.HAction.Execute("InsertWatermark", pset.HSet)
            
        except Exception as e:
            self._logger.error(f"이미지 워터마크 삽입 실패: {e}")
            raise
    
    def batch_apply_watermark(
        self,
        source_files: list[str],
        config: WatermarkConfig,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[WatermarkResult]:
        """
        일괄 워터마크 적용
        
        Args:
            source_files: 파일 목록
            config: 워터마크 설정
            output_dir: 출력 디렉토리 (None이면 원본 위치)
            progress_callback: 진행률 콜백
        
        Returns:
            결과 리스트
        """
        results: list[WatermarkResult] = []
        total = len(source_files)
        
        try:
            self._ensure_hwp()
            
            for idx, source_path in enumerate(source_files):
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                # 출력 경로 결정
                if output_dir:
                    from ..utils.output_paths import resolve_output_path

                    output_path = resolve_output_path(output_dir, source_path)
                else:
                    output_path = None
                
                result = self.apply_watermark(source_path, config, output_path)
                results.append(result)
                
                if (idx + 1) % 50 == 0:
                    gc.collect()
                    
        except Exception as e:
            for remaining in source_files[len(results):]:
                results.append(WatermarkResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results
    
    def remove_watermark(
        self,
        source_path: str,
        output_path: Optional[str] = None
    ) -> WatermarkResult:
        """
        워터마크 제거
        
        Args:
            source_path: 원본 파일 경로
            output_path: 출력 경로
        
        Returns:
            결과
        """
        try:
            hwp = self._get_hwp()
            
            hwp.open(source_path)
            
            # 워터마크 제거
            try:
                hwp.HAction.Run("DeleteWatermark")
            except Exception:
                # 워터마크가 없는 경우 무시하지만 로그는 남김
                self._logger.debug("삭제할 워터마크가 없음")
            
            save_path = output_path if output_path else source_path
            hwp.save_as(save_path)
            
            return WatermarkResult(
                success=True,
                source_path=source_path,
                output_path=save_path
            )
            
        except Exception as e:
            return WatermarkResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )
