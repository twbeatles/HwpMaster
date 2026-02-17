"""
Worker Module
QThread 湲곕컲 諛깃렇?쇱슫???묒뾽 泥섎━

Author: HWP Master
"""

from typing import Any, Optional, Callable, TYPE_CHECKING, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from itertools import chain

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
    """WorkerResult.data??怨듯넻 ?ㅻ? 媛뺤젣?섎뒗 ?ы띁"""
    data: dict[str, Any] = {
        "cancelled": bool(cancelled),
        "success_count": int(success_count),
        "fail_count": int(fail_count),
    }
    data.update(extra)
    return data


class WorkerState(Enum):
    """?묒뾽???곹깭"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class WorkerResult:
    """?묒뾽 寃곌낵"""
    success: bool
    data: Any = None
    error_message: Optional[str] = None


class BaseWorker(QThread):
    """湲곕낯 ?묒뾽???대옒??"""
    
    # ?쒓렇???뺤쓽
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
        """?묒뾽 痍⑥냼 ?붿껌"""
        with QMutexLocker(self._mutex):
            self._cancel_requested = True
            self._state = WorkerState.CANCELLED
    
    def is_cancelled(self) -> bool:
        """痍⑥냼 ?붿껌 ?뺤씤"""
        with QMutexLocker(self._mutex):
            return self._cancel_requested
    
    def run(self) -> None:
        """?묒뾽 ?ㅽ뻾 (?쒕툕?대옒?ㅼ뿉??援ы쁽)"""
        raise NotImplementedError

    def _emit_finished_once(self, result: WorkerResult) -> None:
        with QMutexLocker(self._mutex):
            if self._result_emitted:
                return
            self._result_emitted = True
        self.finished_with_result.emit(result)


class ConversionWorker(BaseWorker):
    """蹂???묒뾽??"""
    
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
        """蹂???ㅽ뻾"""
        from ..core.hwp_handler import HwpHandler, ConvertFormat

        self.state = WorkerState.RUNNING
        self.status_changed.emit("蹂??以鍮?以?..")
        
        # ?щ㎎ 留ㅽ븨
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
                    # 痍⑥냼 ?뺤씤
                    if self.is_cancelled():
                        self.status_changed.emit("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "results": results,
                            }
                        ))
                        return
                    
                    # 吏꾪뻾瑜??낅뜲?댄듃
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"蹂??以? {filename}")
                    
                    # 蹂???ㅽ뻾
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
    """蹂묓빀 ?묒뾽??"""
    
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
        """蹂묓빀 ?ㅽ뻾"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("蹂묓빀 以鍮?以?..")
        
        try:
            with com_context(), HwpHandler() as handler:
                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"蹂묓빀 以? {name}")
                
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
    """?곗씠??二쇱엯 ?묒뾽??"""

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

    @staticmethod
    def _estimate_csv_rows(data_path: Path) -> int:
        encodings = ["utf-8", "cp949"]
        for enc in encodings:
            try:
                with open(data_path, "r", encoding=enc, newline="") as f:
                    total = sum(1 for _ in f)
                return max(0, total - 1)
            except Exception:
                continue
        return -1

    @staticmethod
    def _estimate_excel_rows(data_path: Path) -> int:
        try:
            from openpyxl import load_workbook

            wb = load_workbook(str(data_path), data_only=True, read_only=True)
            try:
                ws = wb.active
                if ws is None:
                    return -1
                max_row = int(getattr(ws, "max_row", 0) or 0)
                return max(0, max_row - 1)
            finally:
                wb.close()
        except Exception:
            return -1

    @staticmethod
    def _iter_csv_rows(data_path: Path) -> Iterator[dict[str, str]]:
        import csv

        last_error: Optional[Exception] = None
        for enc in ("utf-8", "cp949"):
            try:
                with open(data_path, "r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        normalized = {str(k): "" if v is None else str(v) for k, v in row.items()}
                        first_value = next(iter(normalized.values()), "") if normalized else ""
                        if first_value == "":
                            continue
                        yield normalized
                return
            except Exception as e:
                last_error = e

        if last_error:
            raise last_error

    @staticmethod
    def _iter_excel_rows(data_path: Path) -> Iterator[dict[str, str]]:
        from ..core.excel_handler import ExcelHandler

        for chunk in ExcelHandler.read_excel_streaming(str(data_path), chunk_size=200):
            for row in chunk:
                yield {str(k): "" if v is None else str(v) for k, v in row.items()}

    def run(self) -> None:
        """?곗씠??二쇱엯 ?ㅽ뻾"""
        from ..core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("?곗씠??二쇱엯 以鍮?以?..");

        success_count = 0
        fail_count = 0

        try:
            self.status_changed.emit("?곗씠???뚯씪 ?쎈뒗 以?..");
            data_path = Path(self._data_file)
            if not data_path.exists():
                self.state = WorkerState.ERROR
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message=f"?곗씠???뚯씪??議댁옱?섏? ?딆뒿?덈떎: {self._data_file}",
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                ))
                return

            if self.is_cancelled():
                raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")

            if data_path.suffix.lower() == ".csv":
                total_rows = self._estimate_csv_rows(data_path)
                row_iter = self._iter_csv_rows(data_path)
            else:
                total_rows = self._estimate_excel_rows(data_path)
                row_iter = self._iter_excel_rows(data_path)

            try:
                first_row = next(row_iter)
            except StopIteration:
                self.state = WorkerState.ERROR
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message="?곗씠???뚯씪??鍮꾩뼱?덉뒿?덈떎.",
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                ))
                return

            all_rows = chain([first_row], row_iter)

            with com_context(), HwpHandler() as handler:
                out_dir = ensure_dir(self._output_dir)

                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                    shown_total = total_rows if total_rows > 0 else total
                    self.progress.emit(current, shown_total, name)
                    self.status_changed.emit(f"?앹꽦 以? {current}/{shown_total if shown_total > 0 else '?'}")

                for r in handler.iter_inject_data(
                    template_path=self._template_path,
                    data_iterable=all_rows,
                    output_dir=out_dir,
                    filename_field=self._filename_field,
                    progress_callback=progress_cb,
                    total_count=total_rows if total_rows > 0 else None,
                ):
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
    """硫뷀??곗씠???뺣━ ?묒뾽??"""
    
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
        """硫뷀??곗씠???뺣━ ?ㅽ뻾"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("硫뷀??뺣낫 ?뺣━ 以鍮?以?..")
        
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
                        self.status_changed.emit("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
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
                    self.status_changed.emit(f"?뺣━ 以? {filename}")
                    
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
    """遺꾪븷 ?묒뾽??"""
    
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
        """遺꾪븷 ?ㅽ뻾"""
        from ..core.hwp_handler import HwpHandler
        
        self.state = WorkerState.RUNNING
        self.status_changed.emit("遺꾪븷 以鍮?以?..")
        
        success_count = 0
        fail_count = 0
        
        try:
            with com_context(), HwpHandler() as handler:
                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"遺꾪븷 以? {current}/{total}")
                
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
    """?대?吏 異붿텧 ?묒뾽??"""
    
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
        self.status_changed.emit("?대?吏 異붿텧 以鍮?以?..")
        
        # ?대┰蹂대뱶 肄쒕갚 ?뺤쓽 (Worker ?ㅻ젅?쒖뿉???ㅽ뻾?⑥뿉 二쇱쓽)
        # ?섏?留??대┰蹂대뱶??硫붿씤 ?ㅻ젅?쒖뿉???묎렐?댁빞 ???섎룄 ?덉쓬.
        # ?쇰떒 ImageExtractor?먯꽌 肄쒕갚???듯빐 硫붿씤 ?ㅻ젅?쒖쓽 ?숈옉???좊룄?섍굅??
        # ?ш린?쒕뒗 ?⑥닚???뚯씪 泥섎━??吏묒쨷.
        # *二쇱쓽*: refactor濡??명빐 ImageExtractor??clipboard_callback??諛쏆쓬.
        # Worker?먯꽌 ?뚮┫ ?뚮뒗 win32 api ?깆쓣 ?곗? ?딅뒗 ???대┰蹂대뱶 ?묎렐???대젮?????덉쓬.
        # 洹몃윭??ImageExtractor??fallback?대굹 file save 諛⑹떇???대떎硫?臾몄젣 ?놁쓬.
        # ?ш린?쒕뒗 ?⑥닚???ㅽ뻾.
        
        success_count = 0
        fail_count = 0
        total_images = 0
        collected: list[tuple[str, str]] = []
        
        try:
            # ?대┰蹂대뱶 泥섎━瑜??꾪빐 硫붿씤 ?ㅻ젅?쒖? ?듭떊???꾩슂?????덉쑝??
            # ?꾩옱 援ъ“??蹂듭옟?섎?濡?None ?꾨떖 (寃쎄퀬 濡쒓렇 李랁옒)
            # 媛쒖꽑?? 硫붿씤 ?ㅻ젅?쒖뿉 ?붿껌?섎뒗 諛⑹떇 援ы쁽 ?꾩슂 媛?μ꽦
            
            with com_context(), ImageExtractor() as extractor:
                total = len(self._files)
                
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self.status_changed.emit("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
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
                    self.status_changed.emit(f"異붿텧 以? {filename}")
                    
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
    """遺곷쭏???묒뾽??(??젣/?대낫?닿린)"""
    
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
        self.status_changed.emit("遺곷쭏???묒뾽 以鍮?以?..")
        
        try:
            with com_context(), BookmarkManager() as manager:
                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"泥섎━ 以? {name}")

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
                            WorkerResult(success=False, error_message="異쒕젰 ?대뜑媛 ?꾩슂?⑸땲??")
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
                            # UI ?쒖떆瑜??꾪빐 (?뚯씪紐? 遺곷쭏?ъ젙蹂? ?쒗뵆 ???
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
    """?섏씠?쇰쭅??寃???묒뾽??"""

    def __init__(
        self,
        files: list[str],
        output_dir: str,
        *,
        external_requests_enabled: bool = True,
        timeout_sec: int = 5,
        domain_allowlist: str = "",
        max_concurrency: Optional[int] = None,
        cache_enabled: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._external_requests_enabled = bool(external_requests_enabled)
        self._timeout_sec = int(timeout_sec)
        self._domain_allowlist = str(domain_allowlist)
        self._max_concurrency = max_concurrency
        self._cache_enabled = bool(cache_enabled)

    def run(self) -> None:
        from ..core.hyperlink_checker import HyperlinkChecker

        self.state = WorkerState.RUNNING
        self.status_changed.emit("留곹겕 寃??以鍮?以?..");

        success_count = 0
        fail_count = 0
        total_links = 0
        all_links = []

        try:
            with com_context(), HyperlinkChecker(
                external_requests_enabled=self._external_requests_enabled,
                timeout_sec=self._timeout_sec,
                domain_allowlist=self._domain_allowlist,
                max_concurrency=self._max_concurrency,
                cache_enabled=self._cache_enabled,
            ) as checker:
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self.status_changed.emit("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
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
                    self.status_changed.emit(f"寃??以? {filename}")

                    result = checker.check_links(file_path)

                    if result.success:
                        if self._output_dir:
                            report_path = resolve_output_path(self._output_dir, file_path, new_ext="html", suffix="_report")
                            checker.generate_report(result, report_path)

                        success_count += 1
                        total_links += len(result.links)
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
                    "links": all_links,
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
    """?ㅻ뜑/?명꽣 ?묒뾽??"""
    
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
        self.status_changed.emit("?묒뾽 以鍮?以?..")
        
        try:
            with com_context(), HeaderFooterManager() as manager:
                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"泥섎━ 以? {name}")
                
                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(
                            WorkerResult(success=False, error_message="?ㅻ뜑/?명꽣 ?ㅼ젙???꾩슂?⑸땲??")
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
    """?뚰꽣留덊겕 ?묒뾽??"""
    
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
        self.status_changed.emit("?묒뾽 以鍮?以?..")
        
        try:
            with com_context(), WatermarkManager() as manager:
                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("?묒뾽??痍⑥냼?섏뿀?듬땲??")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"泥섎━ 以? {name}")
                
                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(
                            WorkerResult(success=False, error_message="?뚰꽣留덊겕 ?ㅼ젙???꾩슂?⑸땲??")
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
    """?뺢퇋??移섑솚 ?묒뾽??(UI ?ㅻ젅??釉붾줈??諛⑹?)"""

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
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
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
                    self.status_changed.emit(f"移섑솚 以? {Path(file_path).name}")

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
    """?쒖떇 ?듭씪 ?묒뾽??"""

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
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
                            data={
                                "cancelled": True,
                                "success_count": success_count,
                                "fail_count": fail_count,
                                "results": results,
                            },
                        ))
                        return

                    self.progress.emit(idx, total, Path(file_path).name)
                    self.status_changed.emit(f"?곸슜 以? {Path(file_path).name}")

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
    """???ㅽ????묒뾽??"""

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
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
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
                    self.status_changed.emit(f"?곸슜 以? {Path(file_path).name}")

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
    """臾몄꽌 鍮꾧탳 ?묒뾽??"""

    def __init__(self, file1: str, file2: str, parent=None) -> None:
        super().__init__(parent)
        self._file1 = file1
        self._file2 = file2

    def run(self) -> None:
        from ..core.doc_diff import DocDiff

        self.state = WorkerState.RUNNING
        self.status_changed.emit("鍮꾧탳 以鍮?以?..")

        try:
            with com_context():
                if self.is_cancelled():
                    self.state = WorkerState.CANCELLED
                    self._emit_finished_once(WorkerResult(
                        success=False,
                        error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
                        data={"cancelled": True, "success_count": 0, "fail_count": 0},
                    ))
                    return

                self.progress.emit(1, 3, "?띿뒪??異붿텧")
                self.status_changed.emit("?띿뒪??異붿텧 以?..")
                diff = DocDiff()
                result = diff.compare(self._file1, self._file2)

            if self.is_cancelled():
                self.state = WorkerState.CANCELLED
                self._emit_finished_once(WorkerResult(
                    success=False,
                    error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
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
    """紐⑹감 異붿텧 ?묒뾽??"""

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self._file_path = file_path

    def run(self) -> None:
        from ..core.smart_toc import SmartTOC

        self.state = WorkerState.RUNNING
        self.status_changed.emit("紐⑹감 異붿텧 以鍮?以?..")

        try:
            with com_context():
                if self.is_cancelled():
                    self.state = WorkerState.CANCELLED
                    self._emit_finished_once(WorkerResult(
                        success=False,
                        error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
                        data={"cancelled": True, "success_count": 0, "fail_count": 0},
                    ))
                    return

                self.progress.emit(1, 2, "遺꾩꽍")
                self.status_changed.emit("臾몄꽌 遺꾩꽍 以?..")
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
    """留ㅽ겕濡??ㅽ뻾 ?묒뾽??"""

    def __init__(self, macro_id: str, parent=None) -> None:
        super().__init__(parent)
        self._macro_id = macro_id

    def run(self) -> None:
        from ..core.macro_recorder import MacroRecorder
        from ..core.hwp_handler import HwpHandler
        from datetime import datetime

        self.state = WorkerState.RUNNING
        self.status_changed.emit("留ㅽ겕濡??ㅽ뻾 以鍮?以?..")

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
                        error_message="留ㅽ겕濡쒕? 李얠쓣 ???놁뒿?덈떎.",
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
                            error_message="?ъ슜?먭? ?묒뾽??痍⑥냼?덉뒿?덈떎.",
                            data={"cancelled": True, "success_count": 0, "fail_count": 0},
                        ))
                        return

                    self.progress.emit(idx, max(total, 1), action.description or action.action_type)
                    self.status_changed.emit(f"?ㅽ뻾 以? {action.description or action.action_type}")
                    recorder._execute_action(hwp, action)  # pyhwpx ?명솚 ?ㅽ뻾

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


