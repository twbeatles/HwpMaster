"""
Worker Module
QThread 기반 백그라운드 작업 처리

Author: HWP Master
"""

from typing import Any, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

if TYPE_CHECKING:
    from ..core.header_footer_manager import HeaderFooterConfig
    from ..core.watermark_manager import WatermarkConfig

from .com_init import com_context
from .output_paths import ensure_dir, resolve_output_path


def make_summary_data(
    *,
    cancelled: bool,
    success_count: int,
    fail_count: int,
    **extra: Any,
) -> dict[str, Any]:
    """WorkerResult.data에 공통 키를 강제하는 헬퍼"""
    data: dict[str, Any] = {
        "cancelled": bool(cancelled),
        "success_count": int(success_count),
        "fail_count": int(fail_count),
    }
    data.update(extra)
    return data


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
        self._result_emitted = False
    
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

    def _emit_finished_once(self, result: WorkerResult) -> None:
        with QMutexLocker(self._mutex):
            if self._result_emitted:
                return
            self._result_emitted = True
        self.finished_with_result.emit(result)


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
            with com_context(), HwpHandler() as handler:
                total = len(self._files)

                out_dir: Optional[str] = None
                if self._output_dir:
                    out_dir = ensure_dir(self._output_dir)
                
                for idx, file_path in enumerate(self._files, start=1):
                    # 취소 확인
                    if self.is_cancelled():
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "results": results,
                            }
                        ))
                        return
                    
                    # 진행률 업데이트
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"변환 중: {filename}")
                    
                    # 변환 실행
                    if out_dir:
                        output_path = resolve_output_path(
                            out_dir,
                            file_path,
                            new_ext=target_format.value,
                        )
                    else:
                        output_path = None
                    
                    result = handler.convert(file_path, target_format, output_path)
                    results.append(result)
                    
                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0) and not self.is_cancelled(),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results
                }
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results,
                },
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
            with com_context(), HwpHandler() as handler:
                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"병합 중: {name}")
                
                result = handler.merge_files(
                    self._files,
                    self._output_path,
                    progress_callback=progress_cb
                )
            
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=result.success,
                data={
                    "cancelled": False,
                    "success_count": 1 if result.success else 0,
                    "fail_count": 0 if result.success else 1,
                    "result": result,
                },
                error_message=result.error_message,
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": True, "success_count": 0, "fail_count": 0},
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": 1},
            ))


class DataInjectWorker(BaseWorker):
    """데이터 주입 작업자"""
    
    def __init__(
        self,
        template_path: str,
        data_file: str,
        output_dir: str,
        filename_field: Optional[str] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._template_path = template_path
        self._data_file = data_file
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
            # 데이터 파일 읽기 (UI 스레드 프리즈 방지)
            self.status_changed.emit("데이터 파일 읽는 중...")
            from pathlib import Path
            from ..core.excel_handler import ExcelHandler

            data_rows: list[dict[str, str]] = []
            data_path = Path(self._data_file)
            if not data_path.exists():
                self.state = WorkerState.ERROR
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message=f"데이터 파일이 존재하지 않습니다: {self._data_file}",
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                ))
                return

            if self.is_cancelled():
                raise InterruptedError("작업이 취소되었습니다.")

            excel = ExcelHandler()
            if data_path.suffix.lower() == ".csv":
                read_result = excel.read_csv(str(data_path))
            else:
                read_result = excel.read_excel(str(data_path))

            if not read_result.success:
                self.state = WorkerState.ERROR
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message=read_result.error_message or "데이터 파일 읽기에 실패했습니다.",
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                ))
                return

            if not read_result.data:
                self.state = WorkerState.ERROR
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message="데이터 파일이 비어있습니다.",
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                ))
                return

            for row in read_result.data:
                normalized_row = {str(k): "" if v is None else str(v) for k, v in row.items()}
                data_rows.append(normalized_row)

            with com_context(), HwpHandler() as handler:
                out_dir = ensure_dir(self._output_dir)

                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"생성 중: {current}/{total}")
                
                results = handler.batch_inject_data(
                    self._template_path,
                    data_rows,
                    out_dir,
                    self._filename_field,
                    progress_callback=progress_cb
                )
                
                for r in results:
                    if r.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "output_dir": out_dir,
                }
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": True,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
            ))


class MetadataCleanWorker(BaseWorker):
    """메타데이터 정리 작업자"""
    
    def __init__(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        options: Optional[dict[str, bool]] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        
        self._files = files
        self._output_dir = output_dir
        self._options = options
    
    def run(self) -> None:
        """메타데이터 정리 실행"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("메타정보 정리 준비 중...")
        
        success_count = 0
        fail_count = 0
        
        try:
            with com_context(), HwpHandler() as handler:
                total = len(self._files)

                out_dir: Optional[str] = None
                if self._output_dir:
                    out_dir = ensure_dir(self._output_dir)
                
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                            }
                        ))
                        return
                    
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"정리 중: {filename}")
                    
                    output_path = None
                    if out_dir:
                        output_path = resolve_output_path(out_dir, file_path, suffix="_metadata_cleaned")

                    result = handler.clean_metadata(file_path, output_path=output_path, options=self._options)
                    
                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
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
            with com_context(), HwpHandler() as handler:
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
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": True,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
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
        fail_count = 0
        total_images = 0
        collected: list[tuple[str, str]] = []
        
        try:
            # 클립보드 처리를 위해 메인 스레드와 통신이 필요할 수 있으나,
            # 현재 구조상 복잡하므로 None 전달 (경고 로그 찍힘)
            # 개선점: 메인 스레드에 요청하는 방식 구현 필요 가능성
            
            with com_context(), ImageExtractor() as extractor:
                total = len(self._files)
                
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "total_images": total_images,
                                "images": collected,
                            },
                        ))
                        return
                        
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
                        for img in result.images[:10]:
                            collected.append((filename, img.saved_path))
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_images": total_images,
                    "images": collected,
                },
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_images": total_images,
                    "images": collected,
                },
            ))


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
            with com_context(), BookmarkManager() as manager:
                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")

                if self._mode == "delete":
                    results = manager.batch_delete_bookmarks(
                        self._files, 
                        self._output_dir,
                        progress_callback=progress_cb
                    )
                    success_count = sum(1 for r in results if r.success)
                    fail_count = len(self._files) - success_count
                    data = {"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)}
                
                elif self._mode == "export":
                    if self._output_dir is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(
                            WorkerResult(success=False, error_message="출력 폴더가 필요합니다.")
                        )
                        return

                    results = manager.batch_export_bookmarks(
                        self._files,
                        self._output_dir,
                        progress_callback=progress_cb
                    )
                    success_count = sum(1 for r in results if r.success)
                    fail_count = len(self._files) - success_count
                    data = {"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)}
                
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
                    fail_count = len(results) - success_count
                    data = {"cancelled": False, "success_count": success_count, "fail_count": fail_count, "bookmarks": all_bookmarks}
                
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=True,
                data=data
            ))

            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": True, "success_count": 0, "fail_count": 0},
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": 1},
            ))


class HyperlinkWorker(BaseWorker):
    """하이퍼링크 검사 작업자"""
    
    def __init__(
        self,
        files: list[str],
        output_dir: str,
        *,
        external_requests_enabled: bool = True,
        timeout_sec: int = 5,
        domain_allowlist: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._external_requests_enabled = bool(external_requests_enabled)
        self._timeout_sec = int(timeout_sec)
        self._domain_allowlist = str(domain_allowlist)
    
    def run(self) -> None:
        from ..core.hyperlink_checker import HyperlinkChecker
        from pathlib import Path
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("링크 검사 준비 중...")
        
        success_count = 0
        fail_count = 0
        total_links = 0
        all_links = []
        
        try:
            with com_context(), HyperlinkChecker(
                external_requests_enabled=self._external_requests_enabled,
                timeout_sec=self._timeout_sec,
                domain_allowlist=self._domain_allowlist,
            ) as checker:
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "total_links": total_links,
                                "links": all_links,
                            },
                        ))
                        return
                    
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"검사 중: {filename}")
                    
                    result = checker.check_links(file_path)
                    
                    if result.success:
                        # 리포트 생성
                        if self._output_dir:
                            report_path = resolve_output_path(self._output_dir, file_path, new_ext="html", suffix="_report")
                            checker.generate_report(result, report_path)
                        
                        success_count += 1
                        total_links += len(result.links)
                        
                        # UI 표시 데이터 수집
                        for link in result.links:
                            all_links.append((filename, link))
                    else:
                        fail_count += 1
            
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count, 
                    "fail_count": fail_count,
                    "total_links": total_links,
                    "links": all_links
                }
            ))
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_links": total_links,
                    "links": all_links,
                },
            ))


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
            with com_context(), HeaderFooterManager() as manager:
                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")
                
                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(
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
                fail_count = len(results) - success_count
                
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=True,
                data={"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)}
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": True, "success_count": 0, "fail_count": 0},
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": 1},
            ))


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
            with com_context(), WatermarkManager() as manager:
                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")
                
                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(
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
                fail_count = len(results) - success_count
                
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=True,
                data={"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)}
            ))
            
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": True, "success_count": 0, "fail_count": 0},
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": 1},
            ))


class RegexReplaceWorker(BaseWorker):
    """정규식 치환 작업자 (UI 스레드 블로킹 방지)"""

    def __init__(
        self,
        files: list[str],
        rules: list[Any],
        output_dir: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._rules = rules
        self._output_dir = output_dir

    def run(self) -> None:
        from ..core.regex_replacer import RegexReplacer

        self.state = WorkerState.RUNNING
        out_dir = ensure_dir(self._output_dir)

        success_count = 0
        fail_count = 0
        total_replaced = 0
        total_replaced_known = True
        per_file: dict[str, dict[str, int]] = {}

        try:
            with com_context():
                replacer = RegexReplacer()
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "total_replaced": total_replaced,
                                "total_replaced_known": total_replaced_known,
                                "results": per_file,
                            },
                        ))
                        return

                    self.progress.emit(idx, total, Path(file_path).name)
                    self.status_changed.emit(f"치환 중: {Path(file_path).name}")

                    output_path = resolve_output_path(out_dir, file_path)
                    res = replacer.replace_in_hwp(file_path, self._rules, output_path=output_path)
                    per_file[Path(file_path).name] = res

                    if "_error" in res:
                        fail_count += 1
                    else:
                        success_count += 1
                        vals = list(res.values())
                        if any(v < 0 for v in vals):
                            total_replaced_known = False
                        total_replaced += sum(v for v in vals if v >= 0)

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_replaced": total_replaced,
                    "total_replaced_known": total_replaced_known,
                    "results": per_file,
                    "output_dir": out_dir,
                },
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_replaced": total_replaced,
                    "total_replaced_known": total_replaced_known,
                    "results": per_file,
                },
            ))


class StyleCopWorker(BaseWorker):
    """서식 통일 작업자"""

    def __init__(self, files: list[str], rule: Any, output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._rule = rule
        self._output_dir = output_dir

    def run(self) -> None:
        from ..core.style_cop import StyleCop

        self.state = WorkerState.RUNNING
        out_dir = ensure_dir(self._output_dir)

        success_count = 0
        fail_count = 0
        results: list[Any] = []

        try:
            with com_context():
                cop = StyleCop()
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "results": results,
                            },
                        ))
                        return

                    self.progress.emit(idx, total, Path(file_path).name)
                    self.status_changed.emit(f"적용 중: {Path(file_path).name}")

                    output_path = resolve_output_path(out_dir, file_path)
                    res = cop.apply_style(file_path, self._rule, output_path=output_path)
                    results.append(res)
                    if getattr(res, "success", False):
                        success_count += 1
                    else:
                        fail_count += 1

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results,
                    "output_dir": out_dir,
                },
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results,
                },
            ))


class TableDoctorWorker(BaseWorker):
    """표 스타일 작업자"""

    def __init__(self, files: list[str], style: Any, output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._style = style
        self._output_dir = output_dir

    def run(self) -> None:
        from ..core.table_doctor import TableDoctor

        self.state = WorkerState.RUNNING
        out_dir = ensure_dir(self._output_dir)

        success_count = 0
        fail_count = 0
        total_tables_fixed = 0
        results: list[Any] = []

        try:
            with com_context():
                doctor = TableDoctor()
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "tables_fixed": total_tables_fixed,
                                "results": results,
                            },
                        ))
                        return

                    self.progress.emit(idx, total, Path(file_path).name)
                    self.status_changed.emit(f"적용 중: {Path(file_path).name}")

                    output_path = resolve_output_path(out_dir, file_path)
                    res = doctor.apply_style(file_path, self._style, output_path=output_path)
                    results.append(res)
                    if getattr(res, "success", False):
                        success_count += 1
                        total_tables_fixed += int(getattr(res, "tables_fixed", 0) or 0)
                    else:
                        fail_count += 1

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "tables_fixed": total_tables_fixed,
                    "results": results,
                    "output_dir": out_dir,
                },
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "tables_fixed": total_tables_fixed,
                    "results": results,
                },
            ))


class DocDiffWorker(BaseWorker):
    """문서 비교 작업자"""

    def __init__(self, file1: str, file2: str, parent=None) -> None:
        super().__init__(parent)
        self._file1 = file1
        self._file2 = file2

    def run(self) -> None:
        from ..core.doc_diff import DocDiff

        self.state = WorkerState.RUNNING
        self.status_changed.emit("비교 준비 중...")

        try:
            with com_context():
                if self.is_cancelled():
                    self.state = WorkerState.CANCELLED
                    self._emit_finished_once(WorkerResult(
                        success=False,
                        error_message="사용자가 작업을 취소했습니다.",
                        data={"cancelled": True, "success_count": 0, "fail_count": 0},
                    ))
                    return

                self.progress.emit(1, 3, "텍스트 추출")
                self.status_changed.emit("텍스트 추출 중...")
                diff = DocDiff()
                result = diff.compare(self._file1, self._file2)

            if self.is_cancelled():
                self.state = WorkerState.CANCELLED
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message="사용자가 작업을 취소했습니다.",
                    data={"cancelled": True, "success_count": 0, "fail_count": 0},
                ))
                return

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=bool(getattr(result, "success", False)),
                error_message=getattr(result, "error_message", None),
                data={
                    "cancelled": False,
                    "success_count": 1 if getattr(result, "success", False) else 0,
                    "fail_count": 0 if getattr(result, "success", False) else 1,
                    "result": result,
                },
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": 1},
            ))


class SmartTocWorker(BaseWorker):
    """목차 추출 작업자"""

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self._file_path = file_path

    def run(self) -> None:
        from ..core.smart_toc import SmartTOC

        self.state = WorkerState.RUNNING
        self.status_changed.emit("목차 추출 준비 중...")

        try:
            with com_context():
                if self.is_cancelled():
                    self.state = WorkerState.CANCELLED
                    self._emit_finished_once(WorkerResult(
                        success=False,
                        error_message="사용자가 작업을 취소했습니다.",
                        data={"cancelled": True, "success_count": 0, "fail_count": 0},
                    ))
                    return

                self.progress.emit(1, 2, "분석")
                self.status_changed.emit("문서 분석 중...")
                toc = SmartTOC()
                result = toc.extract_toc(self._file_path)

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=bool(getattr(result, "success", False)),
                error_message=getattr(result, "error_message", None),
                data={
                    "cancelled": False,
                    "success_count": 1 if getattr(result, "success", False) else 0,
                    "fail_count": 0 if getattr(result, "success", False) else 1,
                    "result": result,
                },
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": 1},
            ))


class MacroRunWorker(BaseWorker):
    """매크로 실행 작업자"""

    def __init__(self, macro_id: str, parent=None) -> None:
        super().__init__(parent)
        self._macro_id = macro_id

    def run(self) -> None:
        from ..core.macro_recorder import MacroRecorder
        from ..core.hwp_handler import HwpHandler
        from datetime import datetime

        self.state = WorkerState.RUNNING
        self.status_changed.emit("매크로 실행 준비 중...")

        success_count = 0
        fail_count = 0

        try:
            with com_context(), HwpHandler() as handler:
                recorder = MacroRecorder()
                macro = recorder.get_macro(self._macro_id)
                if not macro:
                    self.state = WorkerState.ERROR
                    self._emit_finished_once(WorkerResult(
                        success=False,
                        error_message="매크로를 찾을 수 없습니다.",
                        data={"cancelled": False, "success_count": 0, "fail_count": 1},
                    ))
                    return

                handler._ensure_hwp()
                hwp = handler._hwp

                total = len(macro.actions)
                for idx, action in enumerate(macro.actions, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={"cancelled": True, "success_count": 0, "fail_count": 0},
                        ))
                        return

                    self.progress.emit(idx, max(total, 1), action.description or action.action_type)
                    self.status_changed.emit(f"실행 중: {action.description or action.action_type}")
                    recorder._execute_action(hwp, action)  # pyhwpx 호환 실행

                macro.run_count += 1
                macro.modified_at = datetime.now().isoformat()
                recorder._save_macros()

                success_count = 1

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=True,
                data={"cancelled": False, "success_count": success_count, "fail_count": fail_count},
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            fail_count = 1
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data={"cancelled": False, "success_count": 0, "fail_count": fail_count},
            ))
