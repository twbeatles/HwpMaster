"""
Bookmark Manager Module
HWP 문서 북마크 관리

Author: HWP Master
"""

import gc
import logging
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

from ..utils.output_paths import resolve_output_path


@dataclass
class BookmarkInfo:
    """북마크 정보"""
    name: str
    page: int
    position: int
    text_preview: str = ""


@dataclass
class BookmarkResult:
    """북마크 작업 결과"""
    success: bool
    source_path: str
    bookmarks: list[BookmarkInfo] = field(default_factory=list)
    error_message: Optional[str] = None


class BookmarkManager:
    """북마크 관리자"""
    
    def __init__(self) -> None:
        self._hwp: Any = None
        self._is_initialized = False
        self._logger = logging.getLogger(__name__)
    
    def _ensure_hwp(self) -> None:
        if self._hwp is None:
            try:
                import pyhwpx
                self._hwp = pyhwpx.Hwp(visible=False)
                self._is_initialized = True
            except ImportError:
                raise RuntimeError("pyhwpx가 설치되어 있지 않습니다.")
            except Exception as e:
                raise RuntimeError(f"한글 프로그램 초기화 실패: {e}")

    def _get_hwp(self) -> Any:
        """초기화된 HWP 인스턴스 반환"""
        self._ensure_hwp()
        if self._hwp is None:
            raise RuntimeError("한글 인스턴스 초기화 실패")
        return self._hwp
    
    def close(self) -> None:
        if self._hwp is not None:
            try:
                self._hwp.quit()
            except Exception as e:
                self._logger.warning(f"HWP 종료 중 오류 (무시됨): {e}")
            finally:
                self._hwp = None
                self._is_initialized = False
                gc.collect()
    
    def __enter__(self):
        self._ensure_hwp()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def get_bookmarks(self, source_path: str) -> BookmarkResult:
        """문서 내 모든 북마크 추출 (pyhwpx 호환)"""
        try:
            hwp = self._get_hwp()
            source = Path(source_path)
            if not source.exists():
                return BookmarkResult(False, source_path, error_message="파일 없음")
            
            hwp.open(source_path)
            bookmarks: list[BookmarkInfo] = []
            
            try:
                # pyhwpx 호환: 컨트롤 순회 방식으로 북마크 탐색
                ctrl: Any = hwp.HeadCtrl
                while ctrl:
                    try:
                        if ctrl.UserDesc == "책갈피":
                            bm_name = str(ctrl.GetSetItem(0))  # 북마크 이름
                            bookmarks.append(BookmarkInfo(name=bm_name, page=0, position=0))
                    except Exception:
                        pass
                    ctrl = ctrl.Next
            except Exception as e:
                self._logger.warning(f"북마크 탐색 중 오류 (컨트롤 순회 실패): {e}")
                # 대안: 문서 내 북마크가 없는 것으로 처리
            
            return BookmarkResult(True, source_path, bookmarks)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))
    
    def delete_bookmark(self, source_path: str, bookmark_name: str, output_path: Optional[str] = None) -> BookmarkResult:
        """특정 북마크 삭제 (pyhwpx 호환)"""
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)
            
            # pyhwpx 호환: 컨트롤 순회하여 해당 북마크 삭제
            try:
                ctrl: Any = hwp.HeadCtrl
                while ctrl:
                    try:
                        if ctrl.UserDesc == "책갈피":
                            bm_name = str(ctrl.GetSetItem(0))
                            if bm_name == bookmark_name:
                                ctrl.Delete()
                                break
                    except Exception:
                        pass
                    ctrl = ctrl.Next
            except Exception as e:
                self._logger.warning(f"북마크 삭제 중 오류: {e}")
            
            save_path = output_path or source_path
            hwp.save_as(save_path)
            return BookmarkResult(True, source_path)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))
    
    def delete_all_bookmarks(self, source_path: str, output_path: Optional[str] = None) -> BookmarkResult:
        """모든 북마크 삭제"""
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            ctrl: Any = hwp.HeadCtrl
            while ctrl:
                next_ctrl = ctrl.Next
                try:
                    if ctrl.UserDesc == "책갈피":
                        ctrl.Delete()
                except Exception as e:
                    self._logger.warning(f"북마크 삭제 실패: {e}")
                ctrl = next_ctrl

            save_path = output_path or source_path
            hwp.save_as(save_path)
            return BookmarkResult(True, source_path)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))

    def delete_selected_bookmarks(
        self,
        source_path: str,
        bookmark_names: list[str],
        output_path: Optional[str] = None,
    ) -> BookmarkResult:
        """선택한 북마크만 삭제"""
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            targets = {str(name).strip() for name in bookmark_names if str(name).strip()}
            if not targets:
                return BookmarkResult(False, source_path, error_message="삭제할 북마크가 없습니다.")

            ctrl: Any = hwp.HeadCtrl
            while ctrl:
                next_ctrl = ctrl.Next
                try:
                    if ctrl.UserDesc == "책갈피":
                        bm_name = str(ctrl.GetSetItem(0))
                        if bm_name in targets:
                            ctrl.Delete()
                except Exception as e:
                    self._logger.warning(f"선택 북마크 삭제 실패: {e}")
                ctrl = next_ctrl

            save_path = output_path or source_path
            hwp.save_as(save_path)
            return BookmarkResult(True, source_path)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))
    
    def export_to_excel(self, source_path: str, excel_path: str) -> BookmarkResult:
        """북마크 목록을 Excel로 내보내기"""
        try:
            result = self.get_bookmarks(source_path)
            if not result.success or not result.bookmarks:
                return BookmarkResult(False, source_path, error_message="북마크 없음")
            
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            if ws is None:
                return BookmarkResult(False, source_path, error_message="Excel 시트 생성 실패")
            ws.title = "북마크 목록"
            ws.append(["번호", "북마크 이름", "페이지"])
            for idx, bm in enumerate(result.bookmarks, 1):
                ws.append([idx, bm.name, bm.page])
            wb.save(excel_path)
            return BookmarkResult(True, source_path, result.bookmarks)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))
    
    def batch_delete_bookmarks(
        self,
        source_files: list[str],
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[BookmarkResult]:
        """
        일괄 북마크 삭제
        """
        results: list[BookmarkResult] = []
        total = len(source_files)
        
        try:
            self._ensure_hwp()
            
            for idx, source_path in enumerate(source_files):
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                output_path = None
                if output_dir:
                    output_path = resolve_output_path(output_dir, source_path)
                
                result = self.delete_all_bookmarks(source_path, output_path)
                results.append(result)
                
                if (idx + 1) % 50 == 0:
                    gc.collect()
                    
        except Exception as e:
            for remaining in source_files[len(results):]:
                results.append(BookmarkResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results

    def batch_delete_selected_bookmarks(
        self,
        selected_map: dict[str, list[str]],
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[BookmarkResult]:
        """파일별 선택 북마크 삭제"""
        results: list[BookmarkResult] = []
        source_files = [str(p) for p in selected_map.keys() if str(p).strip()]
        total = len(source_files)

        try:
            self._ensure_hwp()

            for idx, source_path in enumerate(source_files):
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)

                output_path = None
                if output_dir:
                    output_path = resolve_output_path(output_dir, source_path)

                result = self.delete_selected_bookmarks(
                    source_path,
                    bookmark_names=list(selected_map.get(source_path, []) or []),
                    output_path=output_path,
                )
                results.append(result)

                if (idx + 1) % 50 == 0:
                    gc.collect()
        except Exception as e:
            for remaining in source_files[len(results):]:
                results.append(BookmarkResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e),
                ))

        return results
    
    def batch_export_bookmarks(
        self,
        source_files: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[BookmarkResult]:
        """
        일괄 북마크 내보내기 (Excel)
        """
        results: list[BookmarkResult] = []
        total = len(source_files)
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)
        
        try:
            self._ensure_hwp()
            
            for idx, source_path in enumerate(source_files):
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                excel_path = resolve_output_path(output_dir, source_path, new_ext="xlsx", suffix="_bookmarks")
                
                result = self.export_to_excel(source_path, excel_path)
                results.append(result)
                
                if (idx + 1) % 50 == 0:
                    gc.collect()
                    
        except Exception as e:
            for remaining in source_files[len(results):]:
                results.append(BookmarkResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results
