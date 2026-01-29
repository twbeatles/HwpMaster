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
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "TableStyle":
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
                
                # 표 컨트롤 탐색
                ctrl = hwp.HeadCtrl
                table_idx = 0
                
                while ctrl:
                    if ctrl.CtrlID == "tbl":  # 표 컨트롤
                        try:
                            table_set = ctrl.TableSet
                            row_count = table_set.RowCnt
                            col_count = table_set.ColCnt
                            
                            tables.append(TableInfo(
                                index=table_idx,
                                row_count=row_count,
                                col_count=col_count
                            ))
                            table_idx += 1
                        except Exception as e:
                            self._logger.warning(f"표 정보 추출 실패: {e}")
                    
                    ctrl = ctrl.NextCtrl
                    
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
                
                # 표 컨트롤 탐색 및 수정
                ctrl = hwp.HeadCtrl
                table_count = 0
                fixed_count = 0
                
                while ctrl:
                    if ctrl.CtrlID == "tbl":
                        table_count += 1
                        
                        if progress_callback:
                            progress_callback(table_count, table_count, f"표 {table_count}")
                        
                        try:
                            # 표 선택
                            hwp.SetPosBySet(ctrl)
                            hwp.SelectCtrl()
                            
                            # 표 속성 수정
                            hwp.HAction.GetDefault("TableCellBlock", hwp.HParameterSet.HCellBorderFill.HSet)
                            
                            cell_border = hwp.HParameterSet.HCellBorderFill
                            
                            # 테두리 설정
                            border_width = int(style.border_width * 100)  # 0.01mm 단위
                            
                            cell_border.BorderWidthTop = border_width
                            cell_border.BorderWidthBottom = border_width
                            cell_border.BorderWidthLeft = border_width
                            cell_border.BorderWidthRight = border_width
                            
                            # 셀 여백 설정
                            cell_border.CellMarginTop = int(style.cell_padding_top * 100)
                            cell_border.CellMarginBottom = int(style.cell_padding_bottom * 100)
                            cell_border.CellMarginLeft = int(style.cell_padding_left * 100)
                            cell_border.CellMarginRight = int(style.cell_padding_right * 100)
                            
                            hwp.HAction.Execute("TableCellBlock", hwp.HParameterSet.HCellBorderFill.HSet)
                            
                            fixed_count += 1
                            
                        except Exception as e:
                            self._logger.warning(f"표 {table_count} 수정 실패: {e}")
                        
                        # 선택 해제
                        hwp.Cancel()
                    
                    ctrl = ctrl.NextCtrl
                
                # 저장
                save_path = output_path if output_path else file_path
                hwp.SaveAs(save_path)
                
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
                output_path = str(Path(output_dir) / filename)
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
