"""
Table Doctor Module
표 주치의 - 표 스타일 일괄 변경

Author: HWP Master
"""

import logging

from typing import Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum


class BorderStyle(Enum):
    """테두리 스타일"""
    NONE = "없음"
    THIN = "가는 실선"
    MEDIUM = "중간 실선"
    THICK = "굵은 실선"
    DOUBLE = "이중선"


@dataclass
class TableStyle:
    """표 스타일 규칙"""
    name: str
    border_width: float = 0.4  # mm
    border_color: str = "#000000"
    border_style: str = "thin"
    cell_padding_top: float = 1.0  # mm
    cell_padding_bottom: float = 1.0
    cell_padding_left: float = 2.0
    cell_padding_right: float = 2.0
    header_bg_color: Optional[str] = None  # 헤더 배경색
    alternate_row_color: Optional[str] = None  # 줄무늬 색상
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableStyle":
        return cls(**data)


@dataclass
class TableInfo:
    """표 정보"""
    index: int
    row_count: int
    col_count: int
    has_header: bool = False
    border_consistent: bool = True
    
    
@dataclass
class TableDoctorResult:
    """표 치료 결과"""
    success: bool
    file_path: str
    tables_found: int = 0
    tables_fixed: int = 0
    error_message: Optional[str] = None


class TableDoctor:
    """
    표 주치의
    표 스타일 검사 및 일괄 수정
    """
    
    # 프리셋 정의
    PRESETS: dict[str, TableStyle] = {
        "official": TableStyle(
            name="공문서 표준",
            border_width=0.4,
            border_color="#000000",
            cell_padding_top=1.0,
            cell_padding_bottom=1.0,
            cell_padding_left=2.0,
            cell_padding_right=2.0
        ),
        "modern": TableStyle(
            name="모던 스타일",
            border_width=0.2,
            border_color="#666666",
            cell_padding_top=2.0,
            cell_padding_bottom=2.0,
            cell_padding_left=3.0,
            cell_padding_right=3.0,
            header_bg_color="#f0f0f0"
        ),
        "minimal": TableStyle(
            name="미니멀",
            border_width=0.1,
            border_color="#cccccc",
            cell_padding_top=1.5,
            cell_padding_bottom=1.5,
            cell_padding_left=2.0,
            cell_padding_right=2.0
        ),
        "striped": TableStyle(
            name="줄무늬",
            border_width=0.3,
            border_color="#000000",
            cell_padding_top=1.0,
            cell_padding_bottom=1.0,
            cell_padding_left=2.0,
            cell_padding_right=2.0,
            alternate_row_color="#f5f5f5"
        ),
    }
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._custom_styles: list[TableStyle] = []
    
    def get_presets(self) -> list[TableStyle]:
        """프리셋 목록"""
        return list(self.PRESETS.values())
    
    def get_preset(self, preset_id: str) -> Optional[TableStyle]:
        """프리셋 조회"""
        return self.PRESETS.get(preset_id)
    
    def scan_tables(self, file_path: str) -> list[TableInfo]:
        """
        문서 내 표 스캔
        
        Args:
            file_path: HWP 파일 경로
        
        Returns:
            TableInfo 목록
        """
        tables: list[TableInfo] = []
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                # pyhwpx 호환 방식: 표 찾기
                hwp.Run("MoveDocBegin")
                table_idx = 0
                
                while True:
                    result_found = hwp.Run("TableFind")
                    
                    if not result_found:
                        break
                    
                    # 표 발견, 기본 정보만 저장
                    tables.append(TableInfo(
                        index=table_idx,
                        row_count=0,  # 상세 정보는 표 속성 창에서만 확인 가능
                        col_count=0
                    ))
                    table_idx += 1
                    
                    # 다음 위치로 이동
                    hwp.Run("MoveRight")
                    
        except Exception as e:
            self._logger.error(f"표 스캔 오류: {e}")
        
        return tables
    
    def apply_style(
        self,
        file_path: str,
        style: TableStyle,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> TableDoctorResult:
        """
        표 스타일 적용
        
        Args:
            file_path: HWP 파일 경로
            style: 적용할 스타일
            output_path: 출력 경로
            progress_callback: 진행률 콜백
        
        Returns:
            TableDoctorResult
        """
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                # pyhwpx 호환 방식: 문서 내 표 찾기
                table_count = 0
                fixed_count = 0
                
                # 문서 시작으로 이동
                hwp.Run("MoveDocBegin")
                
                # 표 찾기 및 수정 (반복)
                while True:
                    # 다음 표 찾기
                    result_found = hwp.Run("TableFind")
                    
                    if not result_found:
                        break
                    
                    table_count += 1
                    
                    if progress_callback:
                        progress_callback(table_count, table_count, f"표 {table_count}")
                    
                    try:
                        # 표 전체 선택
                        hwp.Run("TableCellBlockExtend")
                        hwp.Run("TableCellBlock")
                        
                        # 셀 속성 변경 - 테두리 설정
                        try:
                            hwp.HAction.GetDefault("CellBorder", hwp.HParameterSet.HCellBorderFill.HSet)
                            cell_border = hwp.HParameterSet.HCellBorderFill
                            
                            # 테두리 너비 설정 (mm → HwpUnit)
                            border_width = hwp.MiliToHwpUnit(style.border_width)
                            cell_border.BorderWidthLeft = border_width
                            cell_border.BorderWidthRight = border_width
                            cell_border.BorderWidthTop = border_width
                            cell_border.BorderWidthBottom = border_width
                            
                            hwp.HAction.Execute("CellBorder", cell_border.HSet)
                            fixed_count += 1
                        except Exception as style_e:
                            self._logger.warning(f"표 {table_count} 스타일 적용 실패: {style_e}")
                        
                        hwp.Run("Cancel")  # 선택 해제
                        
                    except Exception as e:
                        self._logger.warning(f"표 {table_count} 수정 실패: {e}")
                        hwp.Run("Cancel")
                    
                    # 다음 위치로 이동
                    hwp.Run("MoveRight")
                
                # 저장 (pyhwpx 메서드 사용)
                save_path = output_path if output_path else file_path
                hwp.save_as(save_path)
                
                return TableDoctorResult(
                    success=True,
                    file_path=save_path,
                    tables_found=table_count,
                    tables_fixed=fixed_count
                )
                
        except Exception as e:
            return TableDoctorResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )
    
    def batch_apply_style(
        self,
        files: list[str],
        style: TableStyle,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[TableDoctorResult]:
        """
        일괄 표 스타일 적용
        """
        from pathlib import Path
        
        results: list[TableDoctorResult] = []
        total = len(files)
        
        for idx, file_path in enumerate(files, start=1):
            filename = Path(file_path).name
            
            if progress_callback:
                progress_callback(idx, total, filename)
            
            if output_dir:
                from ..utils.output_paths import resolve_output_path

                output_path = resolve_output_path(output_dir, file_path)
            else:
                output_path = None
            
            result = self.apply_style(file_path, style, output_path)
            results.append(result)
        
        return results
    
    def create_custom_style(
        self,
        name: str,
        border_width: float = 0.4,
        cell_padding: float = 2.0
    ) -> TableStyle:
        """커스텀 스타일 생성"""
        style = TableStyle(
            name=name,
            border_width=border_width,
            cell_padding_top=cell_padding,
            cell_padding_bottom=cell_padding,
            cell_padding_left=cell_padding,
            cell_padding_right=cell_padding
        )
        self._custom_styles.append(style)
        return style
