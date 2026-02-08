"""
Worker Module
QThread 기반 백그라운드 작업 처리

Author: HWP Master
"""

from typing import Any, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

if TYPE_CHECKING:
    from ..core.header_footer_manager import HeaderFooterConfig
    from ..core.watermark_manager import WatermarkConfig


class WorkerState(Enum):
    """작업자 상태"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class WorkerResult:
    """작업 결과"""
    success: bool
    data: Any = None
    error_message: Optional[str] = None


class BaseWorker(QThread):
    """기본 작업자 클래스"""
    
    # 시그널 정의
    progress = Signal(int, int, str)  # current, total, message
    status_changed = Signal(str)  # status message
    finished_with_result = Signal(object)  # WorkerResult
    error_occurred = Signal(str)  # error message
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        
        self._state = WorkerState.IDLE
        self._mutex = QMutex()
        self._cancel_requested = False
    
    @property
    def state(self) -> WorkerState:
        with QMutexLocker(self._mutex):
            return self._state
    
    @state.setter
    def state(self, value: WorkerState) -> None:
        with QMutexLocker(self._mutex):
            self._state = value
    
    def cancel(self) -> None:
        """작업 취소 요청"""
        with QMutexLocker(self._mutex):
            self._cancel_requested = True
            self._state = WorkerState.CANCELLED
    
    def is_cancelled(self) -> bool:
        """취소 요청 확인"""
        with QMutexLocker(self._mutex):
            return self._cancel_requested
    
    def run(self) -> None:
        """작업 실행 (서브클래스에서 구현)"""
        raise NotImplementedError


class ConversionWorker(BaseWorker):
    """변환 작업자"""
    
    def __init__(
        self,
        files: list[str],
        target_format: str,
        output_dir: Optional[str] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._files = files
        self._target_format = target_format
        self._output_dir = output_dir
    
    def run(self) -> None:
        """변환 실행"""
        from ..core.hwp_handler import HwpHandler, ConvertFormat
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("변환 준비 중...")
        
        # 포맷 매핑
        format_map = {
            "PDF": ConvertFormat.PDF,
            "TXT": ConvertFormat.TXT,
            "HWPX": ConvertFormat.HWPX,
            "JPG": ConvertFormat.JPG,
        }
        
        target_format = format_map.get(self._target_format.upper(), ConvertFormat.PDF)
        
        success_count = 0
        fail_count = 0
        results = []
        
        try:
            with HwpHandler() as handler:
                total = len(self._files)
                
                for idx, file_path in enumerate(self._files, start=1):
                    # 취소 확인
                    if self.is_cancelled():
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self.finished_with_result.emit(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count
                            }
                        ))
                        return
                    
                    # 진행률 업데이트
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"변환 중: {filename}")
                    
                    # 변환 실행
                    if self._output_dir:
                        output_path = str(
                            Path(self._output_dir) /
                            Path(file_path).with_suffix(f".{target_format.value}").name
                        )
                    else:
                        output_path = None
                    
                    result = handler._convert(file_path, target_format, output_path)
                    results.append(result)
                    
                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=fail_count == 0,
                data={
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results
                }
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(
                success=False,
                error_message=str(e)
            ))


class MergeWorker(BaseWorker):
    """병합 작업자"""
    
    def __init__(
        self,
        files: list[str],
        output_path: str,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._files = files
        self._output_path = output_path
    
    def run(self) -> None:
        """병합 실행"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("병합 준비 중...")
        
        try:
            with HwpHandler() as handler:
                def progress_cb(current: int, total: int, name: str) -> None:
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"병합 중: {name}")
                
                result = handler.merge_files(
                    self._files,
                    self._output_path,
                    progress_callback=progress_cb
                )
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=result.success,
                data=result,
                error_message=result.error_message
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(
                success=False,
                error_message=str(e)
            ))


class DataInjectWorker(BaseWorker):
    """데이터 주입 작업자"""
    
    def __init__(
        self,
        template_path: str,
        data_list: list[dict[str, str]],
        output_dir: str,
        filename_field: Optional[str] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._template_path = template_path
        self._data_list = data_list
        self._output_dir = output_dir
        self._filename_field = filename_field
    
    def run(self) -> None:
        """데이터 주입 실행"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("데이터 주입 준비 중...")
        
        success_count = 0
        fail_count = 0
        
        try:
            with HwpHandler() as handler:
                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"생성 중: {current}/{total}")
                
                results = handler.batch_inject_data(
                    self._template_path,
                    self._data_list,
                    self._output_dir,
                    self._filename_field,
                    progress_callback=progress_cb
                )
                
                for r in results:
                    if r.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=fail_count == 0,
                data={
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(
                success=False,
                error_message=str(e)
            ))


class MetadataCleanWorker(BaseWorker):
    """메타데이터 정리 작업자"""
    
    def __init__(
        self,
        files: list[str],
        options: Optional[dict[str, bool]] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._files = files
        self._options = options
    
    def run(self) -> None:
        """메타데이터 정리 실행"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("메타정보 정리 준비 중...")
        
        success_count = 0
        fail_count = 0
        
        try:
            with HwpHandler() as handler:
                total = len(self._files)
                
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self.finished_with_result.emit(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count
                            }
                        ))
                        return
                    
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"정리 중: {filename}")
                    
                    result = handler.clean_metadata(file_path, options=self._options)
                    
                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=fail_count == 0,
                data={
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(
                success=False,
                error_message=str(e)
            ))


class SplitWorker(BaseWorker):
    """분할 작업자"""
    
    def __init__(
        self,
        file_path: str,
        page_ranges: list[str],
        output_dir: str,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._file_path = file_path
        self._page_ranges = page_ranges
        self._output_dir = output_dir
    
    def run(self) -> None:
        """분할 실행"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("분할 준비 중...")
        
        success_count = 0
        fail_count = 0
        
        try:
            with HwpHandler() as handler:
                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"분할 중: {current}/{total}")
                
                results = handler.split_file(
                    self._file_path,
                    self._page_ranges,
                    self._output_dir,
                    progress_callback=progress_cb
                )
                
                for r in results:
                    if r.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=fail_count == 0,
                data={
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(
                success=False,
                error_message=str(e)
            ))


class ImageExtractWorker(BaseWorker):
    """이미지 추출 작업자"""
    
    def __init__(
        self,
        files: list[str],
        output_dir: str,
        prefix: str = "",
        parent=None
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._prefix = prefix
    
    def run(self) -> None:
        from ..core.image_extractor import ImageExtractor
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("이미지 추출 준비 중...")
        
        # 클립보드 콜백 정의 (Worker 스레드에서 실행됨에 주의)
        # 하지만 클립보드는 메인 스레드에서 접근해야 할 수도 있음.
        # 일단 ImageExtractor에서 콜백을 통해 메인 스레드의 동작을 유도하거나,
        # 여기서는 단순히 파일 처리에 집중.
        # *주의*: refactor로 인해 ImageExtractor는 clipboard_callback을 받음.
        # Worker에서 돌릴 때는 win32 api 등을 쓰지 않는 한 클립보드 접근이 어려울 수 있음.
        # 그러나 ImageExtractor의 fallback이나 file save 방식을 쓴다면 문제 없음.
        # 여기서는 단순히 실행.
        
        success_count = 0
        total_images = 0
        
        try:
            # 클립보드 처리를 위해 메인 스레드와 통신이 필요할 수 있으나,
            # 현재 구조상 복잡하므로 None 전달 (경고 로그 찍힘)
            # 개선점: 메인 스레드에 요청하는 방식 구현 필요 가능성
            
            with ImageExtractor() as extractor:
                total = len(self._files)
                
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        break
                        
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"추출 중: {filename}")
                    
                    result = extractor.extract_images(
                        file_path, 
                        self._output_dir, 
                        self._prefix
                    )
                    
                    if result.success:
                        success_count += 1
                        total_images += len(result.images)
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=True,
                data={"success_count": success_count, "total_images": total_images}
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(False, error_message=str(e)))


class BookmarkWorker(BaseWorker):
    """북마크 작업자 (삭제/내보내기)"""
    
    def __init__(
        self,
        mode: str, # "delete" or "export"
        files: list[str],
        output_dir: Optional[str] = None, # for delete (optional) or export (required)
        parent=None
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._output_dir = output_dir
    
    def run(self) -> None:
        from ..core.bookmark_manager import BookmarkManager
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("북마크 작업 준비 중...")
        
        try:
            with BookmarkManager() as manager:
                def progress_cb(current, total, name):
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")

                if self._mode == "delete":
                    results = manager.batch_delete_bookmarks(
                        self._files, 
                        self._output_dir,
                        progress_callback=progress_cb
                    )
                    success_count = sum(1 for r in results if r.success)
                    data = {"success_count": success_count, "total": len(self._files)}
                
                elif self._mode == "export":
                    if self._output_dir is None:
                        self.state = WorkerState.ERROR
                        self.finished_with_result.emit(
                            WorkerResult(success=False, error_message="출력 폴더가 필요합니다.")
                        )
                        return

                    results = manager.batch_export_bookmarks(
                        self._files,
                        self._output_dir,
                        progress_callback=progress_cb
                    )
                    success_count = sum(1 for r in results if r.success)
                    data = {"success_count": success_count, "total": len(self._files)}
                
                else: # extract
                    results = []
                    total = len(self._files)
                    all_bookmarks = []
                    for idx, file_path in enumerate(self._files, start=1):
                        progress_cb(idx, total, file_path)
                        res = manager.get_bookmarks(file_path)
                        results.append(res)
                        if res.success and res.bookmarks:
                            # UI 표시를 위해 (파일명, 북마크정보) 튜플 저장
                            from pathlib import Path
                            fname = Path(file_path).name
                            for bm in res.bookmarks:
                                all_bookmarks.append((fname, bm))
                    
                    success_count = sum(1 for r in results if r.success)
                    data = {"success_count": success_count, "bookmarks": all_bookmarks}
                
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=True,
                data=data
            ))

            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(False, error_message=str(e)))


class HyperlinkWorker(BaseWorker):
    """하이퍼링크 검사 작업자"""
    
    def __init__(self, files: list[str], output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
    
    def run(self) -> None:
        from ..core.hyperlink_checker import HyperlinkChecker
        from pathlib import Path
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("링크 검사 준비 중...")
        
        success_count = 0
        total_links = 0
        all_links = []
        
        try:
            with HyperlinkChecker() as checker:
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        break
                    
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"검사 중: {filename}")
                    
                    result = checker.check_links(file_path)
                    
                    if result.success:
                        # 리포트 생성
                        if self._output_dir:
                            report_name = f"{Path(file_path).stem}_report.html"
                            checker.generate_report(result, str(Path(self._output_dir) / report_name))
                        
                        success_count += 1
                        total_links += len(result.links)
                        
                        # UI 표시 데이터 수집
                        for link in result.links:
                            all_links.append((filename, link))
            
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=True,
                data={
                    "success_count": success_count, 
                    "total_links": total_links,
                    "links": all_links
                }
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(False, error_message=str(e)))


class HeaderFooterWorker(BaseWorker):
    """헤더/푸터 작업자"""
    
    def __init__(
        self,
        mode: str, # "apply" or "remove"
        files: list[str],
        config: Optional["HeaderFooterConfig"] = None,
        output_dir: Optional[str] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._config = config
        self._output_dir = output_dir
    
    def run(self) -> None:
        from ..core.header_footer_manager import HeaderFooterManager
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("작업 준비 중...")
        
        try:
            with HeaderFooterManager() as manager:
                def progress_cb(current, total, name):
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")
                
                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self.finished_with_result.emit(
                            WorkerResult(success=False, error_message="헤더/푸터 설정이 필요합니다.")
                        )
                        return

                    config = self._config
                    results = manager.batch_apply_header_footer(
                        self._files,
                        config,
                        self._output_dir,
                        progress_callback=progress_cb
                    )
                else: # remove
                    results = []
                    total = len(self._files)
                    for idx, file_path in enumerate(self._files, start=1):
                        progress_cb(idx, total, file_path)
                        from pathlib import Path
                        out_path = None
                        if self._output_dir:
                            out_path = str(Path(self._output_dir) / Path(file_path).name)
                        results.append(manager.remove_header_footer(file_path, out_path))
                
                success_count = sum(1 for r in results if r.success)
                
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=True,
                data={"success_count": success_count, "total": len(self._files)}
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(False, error_message=str(e)))


class WatermarkWorker(BaseWorker):
    """워터마크 작업자"""
    
    def __init__(
        self,
        mode: str, # "apply" or "remove"
        files: list[str],
        config: Optional["WatermarkConfig"] = None,
        output_dir: Optional[str] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._config = config
        self._output_dir = output_dir
    
    def run(self) -> None:
        from ..core.watermark_manager import WatermarkManager
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("작업 준비 중...")
        
        try:
            with WatermarkManager() as manager:
                def progress_cb(current, total, name):
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")
                
                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self.finished_with_result.emit(
                            WorkerResult(success=False, error_message="워터마크 설정이 필요합니다.")
                        )
                        return

                    config = self._config
                    results = manager.batch_apply_watermark(
                        self._files,
                        config,
                        self._output_dir,
                        progress_callback=progress_cb
                    )
                else: # remove
                    results = []
                    total = len(self._files)
                    for idx, file_path in enumerate(self._files, start=1):
                        progress_cb(idx, total, file_path)
                        from pathlib import Path
                        out_path = None
                        if self._output_dir:
                            out_path = str(Path(self._output_dir) / Path(file_path).name)
                        results.append(manager.remove_watermark(file_path, out_path))
                
                success_count = sum(1 for r in results if r.success)
                
            self.state = WorkerState.FINISHED
            self.finished_with_result.emit(WorkerResult(
                success=True,
                data={"success_count": success_count, "total": len(self._files)}
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self.finished_with_result.emit(WorkerResult(False, error_message=str(e)))
