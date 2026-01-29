"""
Bookmark Manager Module
HWP 문서 북마크 관리

Author: HWP Master
"""

import gc
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass


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
    bookmarks: list = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.bookmarks is None:
            self.bookmarks = []


class BookmarkManager:
    """북마크 관리자"""
    
    def __init__(self) -> None:
        self._hwp = None
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
        """문서 내 모든 북마크 추출"""
        try:
            self._ensure_hwp()
            source = Path(source_path)
            if not source.exists():
                return BookmarkResult(False, source_path, error_message="파일 없음")
            
            self._hwp.open(source_path)
            bookmarks = []
            
            try:
                bookmark_list = self._hwp.get_bookmark_list()
                for bm_name in bookmark_list:
                    try:
                        self._hwp.goto_bookmark(bm_name)
                        page_num = self._hwp.get_current_page()
                        bookmarks.append(BookmarkInfo(bm_name, page_num, 0))
                    except Exception:
                        bookmarks.append(BookmarkInfo(bm_name, 0, 0))
            except Exception as e:
                self._logger.warning(f"북마크 목록 순회 중 오류: {e}")
            
            return BookmarkResult(True, source_path, bookmarks)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))
    
    def delete_bookmark(self, source_path: str, bookmark_name: str, output_path: Optional[str] = None) -> BookmarkResult:
        """특정 북마크 삭제"""
        try:
            self._ensure_hwp()
            self._hwp.open(source_path)
            self._hwp.delete_bookmark(bookmark_name)
            save_path = output_path or source_path
            self._hwp.save_as(save_path)
            return BookmarkResult(True, source_path)
        except Exception as e:
            return BookmarkResult(False, source_path, error_message=str(e))
    
    def delete_all_bookmarks(self, source_path: str, output_path: Optional[str] = None) -> BookmarkResult:
        """모든 북마크 삭제"""
        try:
            self._ensure_hwp()
            self._hwp.open(source_path)
            result = self.get_bookmarks(source_path)
            for bookmark in result.bookmarks:
                try:
                    self._hwp.delete_bookmark(bookmark.name)
                except Exception as e:
                    self._logger.warning(f"북마크 '{bookmark.name}' 삭제 실패: {e}")
            save_path = output_path or source_path
            self._hwp.save_as(save_path)
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
                    output_path = str(Path(output_dir) / Path(source_path).name)
                
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
                
                excel_name = f"{Path(source_path).stem}_bookmarks.xlsx"
                excel_path = str(output_directory / excel_name)
                
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
