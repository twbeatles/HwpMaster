"""
Worker Module
QThread 기반 백그라운드 작업 처리

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
    """WorkerResult.data의 공통 키를 강제하는 헬퍼."""
    data: dict[str, Any] = {
        "cancelled": bool(cancelled),
        "success_count": int(success_count),
        "fail_count": int(fail_count),
    }
    data.update(extra)
    return data


def _build_failed_summary(results: list[Any], *, max_items: int = 3) -> Optional[str]:
    failed_items: list[str] = []
    for item in results:
        if bool(getattr(item, "success", False)):
            continue
        source_path = str(getattr(item, "source_path", "") or "").strip()
        source_name = Path(source_path).name if source_path else "(unknown)"
        error_message = str(getattr(item, "error_message", "") or "unknown")
        failed_items.append(f"{source_name}: {error_message}")

    if not failed_items:
        return None

    limit = max(1, int(max_items))
    summary = "; ".join(failed_items[:limit])
    remain = len(failed_items) - limit
    if remain > 0:
        summary += f" (+{remain} more)"
    return summary


class WorkerState(Enum):
    """작업 상태."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class WorkerResult:
    """작업 결과."""
    success: bool
    data: Any = None
    error_message: Optional[str] = None


class BaseWorker(QThread):
    """기본 작업자 클래스."""

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
        """작업 취소 요청."""
        with QMutexLocker(self._mutex):
            self._cancel_requested = True
            self._state = WorkerState.CANCELLED

    def is_cancelled(self) -> bool:
        """취소 요청 여부 확인."""
        with QMutexLocker(self._mutex):
            return self._cancel_requested

    def run(self) -> None:
        """작업 실행. 하위 클래스에서 구현한다."""
        raise NotImplementedError

    def _emit_finished_once(self, result: WorkerResult) -> None:
        with QMutexLocker(self._mutex):
            if self._result_emitted:
                return
            self._result_emitted = True
        self.finished_with_result.emit(result)


class ConversionWorker(BaseWorker):
    """문서 변환 작업자."""

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
        """변환 실행."""
        from ..core.hwp_handler import HwpHandler, ConvertFormat

        self.state = WorkerState.RUNNING
        self.status_changed.emit("변환 준비 중...")

        # 형식 매핑
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
                    # 취소 요청 확인
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

                    # 진행 상태 업데이트
                    from pathlib import Path
                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"변환 중: {filename}")

                    # 파일 변환 실행
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
    """문서 병합 작업자."""

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
        """병합 실행."""
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
    """데이터 주입 작업자."""

    def __init__(
        self,
        template_path: str,
        data_file: str,
        output_dir: str,
        filename_field: Optional[str] = None,
        filename_template: Optional[str] = None,
        parent=None
    ) -> None:
        super().__init__(parent)

        self._template_path = template_path
        self._data_file = data_file
        self._output_dir = output_dir
        self._filename_field = filename_field
        self._filename_template = filename_template

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
    def _count_empty_csv_rows(data_path: Path) -> int:
        import csv

        for enc in ("utf-8", "cp949"):
            try:
                count = 0
                with open(data_path, "r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        normalized = {str(k): "" if v is None else str(v).strip() for k, v in row.items()}
                        if normalized and all(v == "" for v in normalized.values()):
                            count += 1
                return count
            except Exception:
                continue
        return 0

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
                        normalized_values = [str(v).strip() for v in normalized.values()]
                        if normalized and all(v == "" for v in normalized_values):
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
        """데이터 주입 실행."""
        from ..core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("데이터 주입 준비 중...")

        success_count = 0
        fail_count = 0
        skipped_empty_rows = 0
        filename_collisions = 0

        try:
            self.status_changed.emit("데이터 파일 확인 중...")
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

            if data_path.suffix.lower() == ".csv":
                total_rows = self._estimate_csv_rows(data_path)
                skipped_empty_rows = self._count_empty_csv_rows(data_path)
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
                    error_message="데이터 파일이 비어 있습니다.",
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                ))
                return

            all_rows = chain([first_row], row_iter)

            with com_context(), HwpHandler() as handler:
                out_dir = ensure_dir(self._output_dir)
                merge_stats: dict[str, int] = {}

                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    shown_total = total_rows if total_rows > 0 else total
                    self.progress.emit(current, shown_total, name)
                    self.status_changed.emit(f"생성 중: {current}/{shown_total if shown_total > 0 else '?'}")

                for r in handler.iter_inject_data(
                    template_path=self._template_path,
                    data_iterable=all_rows,
                    output_dir=out_dir,
                    filename_field=self._filename_field,
                    filename_template=self._filename_template,
                    progress_callback=progress_cb,
                    total_count=total_rows if total_rows > 0 else None,
                    stats=merge_stats,
                ):
                    if r.success:
                        success_count += 1
                    else:
                        fail_count += 1

                filename_collisions = int(merge_stats.get("filename_collisions", 0) or 0)

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "output_dir": out_dir,
                    "skipped_empty_rows": skipped_empty_rows,
                    "filename_collisions": filename_collisions,
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
                    "skipped_empty_rows": skipped_empty_rows,
                    "filename_collisions": filename_collisions,
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
                    "skipped_empty_rows": skipped_empty_rows,
                    "filename_collisions": filename_collisions,
                },
            ))

class MetadataCleanWorker(BaseWorker):
    """메타정보 정리 작업자."""

    def __init__(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
        parent=None
    ) -> None:
        super().__init__(parent)

        self._files = files
        self._output_dir = output_dir
        self._options = options

    def run(self) -> None:
        """메타정보 정리 실행."""
        from ..core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("메타정보 정리 준비 중...")

        success_count = 0
        fail_count = 0
        pii_total = 0
        warnings: list[str] = []
        password_requested = bool(str((self._options or {}).get("document_password", "")).strip())
        password_not_applied = 0

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

                    result = handler.harden_document(file_path, output_path=output_path, options=self._options)
                    artifacts = dict(result.artifacts or {})

                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1

                    pii_total += int(artifacts.get("pii_total", 0) or 0)
                    if password_requested and not bool(artifacts.get("password_applied", False)):
                        password_not_applied += 1

                    for msg in result.warnings:
                        warnings.append(f"{filename}: {msg}")

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=fail_count == 0,
                data={
                    "cancelled": False,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "pii_total": pii_total,
                    "password_not_applied": password_not_applied,
                    "warnings": warnings,
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
                    "pii_total": pii_total,
                    "password_not_applied": password_not_applied,
                    "warnings": warnings,
                },
            ))


class SplitWorker(BaseWorker):
    """문서 분할 작업자."""

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
        """분할 실행."""
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
    """이미지 추출 작업자."""

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

        # 클립보드 접근은 UI 스레드 제약이 있어 주의가 필요하다.
        # 이 Worker는 파일 저장 기반 추출만 담당하고,
        # ImageExtractor 내부 fallback 경로를 그대로 사용한다.
        #
        # 추후 신호 기반 협업이 필요하면 UI 스레드 전용 경로를 추가한다.

        success_count = 0
        fail_count = 0
        total_images = 0
        collected: list[tuple[str, str]] = []

        try:
            # 현재 구현은 UI 스레드와 직접 통신하지 않는다.
            # 필요한 경우 메인 스레드 신호/슬롯 기반 경로를 별도로 추가한다.

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

                    batch_results = extractor.batch_extract(
                        [file_path],
                        self._output_dir,
                        prefix=self._prefix,
                    )
                    if not batch_results:
                        fail_count += 1
                        continue
                    result = batch_results[0]

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
    """북마크 작업자 (삭제/내보내기/추출)."""

    def __init__(
        self,
        mode: str, # "delete" or "export" or "extract" or "delete_selected"
        files: list[str],
        output_dir: Optional[str] = None, # for delete (optional) or export (required)
        selected_map: Optional[dict[str, list[str]]] = None,
        parent=None
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._output_dir = output_dir
        self._selected_map = selected_map or {}

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

                elif self._mode == "delete_selected":
                    results = manager.batch_delete_selected_bookmarks(
                        self._selected_map,
                        self._output_dir,
                        progress_callback=progress_cb,
                    )
                    success_count = sum(1 for r in results if r.success)
                    fail_count = len(results) - success_count
                    data = {
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "total": len(results),
                    }

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
                            # UI 표시를 위해 (원본 파일 경로, 북마크정보) 튜플 전달
                            for bm in res.bookmarks:
                                all_bookmarks.append((str(file_path), bm))

                    success_count = sum(1 for r in results if r.success)
                    fail_count = len(results) - success_count
                    data = {"cancelled": False, "success_count": success_count, "fail_count": fail_count, "bookmarks": all_bookmarks}

            summary_error = None
            if fail_count > 0:
                failed_items = [
                    f"{Path(r.source_path).name}: {r.error_message or 'unknown'}"
                    for r in results
                    if not r.success
                ]
                summary_error = "; ".join(failed_items[:3])
                if len(failed_items) > 3:
                    summary_error += f" (+{len(failed_items) - 3} more)"

            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0),
                error_message=summary_error,
                data=data,
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
    """하이퍼링크 검사 작업자."""

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
        from ..core.hyperlink_checker import HyperlinkChecker, LinkInfo

        self.state = WorkerState.RUNNING
        self.status_changed.emit("링크 검사 준비 중...")

        success_count = 0
        fail_count = 0
        total_links = 0
        all_links: list[tuple[str, LinkInfo]] = []
        report_fail_count = 0
        warnings: list[str] = []

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
                                "report_fail_count": report_fail_count,
                                "warnings": warnings,
                            },
                        ))
                        return

                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"검사 중: {filename}")

                    result = checker.check_links(file_path)

                    if result.success:
                        report_saved = True
                        if self._output_dir:
                            report_path = resolve_output_path(self._output_dir, file_path, new_ext="html", suffix="_report")
                            report_saved = bool(checker.generate_report(result, report_path))
                            if not report_saved:
                                report_fail_count += 1
                                fail_count += 1
                                warnings.append(f"{filename}: 리포트 저장 실패 ({report_path})")

                        if report_saved:
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
                    "report_fail_count": report_fail_count,
                    "warnings": warnings,
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
                    "report_fail_count": report_fail_count,
                    "warnings": warnings,
                },
            ))

class HeaderFooterWorker(BaseWorker):
    """헤더/푸터 작업자."""

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
        self.status_changed.emit("헤더/푸터 작업 준비 중...")

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
                        out_path = None
                        if self._output_dir:
                            out_path = resolve_output_path(self._output_dir, file_path)
                        results.append(manager.remove_header_footer(file_path, out_path))
                success_count = sum(1 for r in results if r.success)
                fail_count = len(results) - success_count
                summary_error = _build_failed_summary(results)
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0),
                error_message=summary_error,
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
    """워터마크 작업자."""

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
        self.status_changed.emit("워터마크 작업 준비 중...")

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
                        out_path = None
                        if self._output_dir:
                            out_path = resolve_output_path(self._output_dir, file_path)
                        results.append(manager.remove_watermark(file_path, out_path))
                success_count = sum(1 for r in results if r.success)
                fail_count = len(results) - success_count
                summary_error = _build_failed_summary(results)
            self.state = WorkerState.FINISHED
            self._emit_finished_once(WorkerResult(
                success=(fail_count == 0),
                error_message=summary_error,
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
    """정규식 치환 작업자."""

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
    """서식 교정 작업자."""

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
    """표 교정 작업자."""

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
                    self.status_changed.emit(f"교정 중: {Path(file_path).name}")

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
    """문서 비교 작업자."""

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
    """목차 추출 작업자."""

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


class ActionConsoleWorker(BaseWorker):
    """고급 액션 콘솔 실행 Worker."""

    def __init__(
        self,
        source_file: str,
        commands: list[dict[str, Any]],
        *,
        stop_on_error: bool = True,
        save_mode: str = "new",
        output_path: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source_file = str(source_file or "")
        self._commands = commands
        self._stop_on_error = bool(stop_on_error)
        self._save_mode = str(save_mode or "new").strip().lower()
        self._output_path = str(output_path or "").strip()

    def run(self) -> None:
        from ..core.action_runner import ActionRunner, ActionCommand
        from ..core.hwp_handler import HwpHandler
        from ..core.macro_recorder import MacroRecorder
        from .settings import get_settings_manager

        self.state = WorkerState.RUNNING
        self.status_changed.emit("액션 실행 준비 중...")

        try:
            with com_context(), HwpHandler() as handler:
                if self._source_file:
                    handler._get_hwp().open(self._source_file)

                normalized: list[ActionCommand] = []
                total = len(self._commands)
                for idx, raw in enumerate(self._commands, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data=make_summary_data(
                                cancelled=True,
                                success_count=0,
                                fail_count=0,
                                changed_count=idx - 1,
                            ),
                        ))
                        return

                    cmd = ActionCommand(
                        action_type=str(raw.get("action_type", "run")),
                        action_id=str(raw.get("action_id", "")),
                        pset_name=str(raw.get("pset_name", "")),
                        values=dict(raw.get("values", {}) or {}),
                        description=str(raw.get("description", "")),
                    ).normalize()
                    normalized.append(cmd)
                    self.progress.emit(idx, max(total, 1), cmd.description or cmd.action_id)
                    self.status_changed.emit(f"준비 중: {cmd.action_type} {cmd.action_id}")

                runner = ActionRunner()
                op = runner.run_commands(
                    normalized,
                    stop_on_error=self._stop_on_error,
                    handler=handler,
                )

                warnings = list(op.warnings or [])
                artifacts = dict(op.artifacts or {})

                recorder = MacroRecorder()
                succeeded_commands = list(artifacts.get("succeeded_commands", []) or [])
                if recorder.is_recording:
                    for command in succeeded_commands:
                        action_type = str(command.get("action_type", "run")).strip().lower()
                        if action_type == "run":
                            recorder.record_action(
                                action_type="run_action",
                                params={
                                    "action_id": str(command.get("action_id", "")),
                                },
                                description=str(command.get("description", "")) or f"Run {command.get('action_id', '')}",
                            )
                        elif action_type == "execute":
                            recorder.record_action(
                                action_type="execute_action",
                                params={
                                    "action_id": str(command.get("action_id", "")),
                                    "pset_name": str(command.get("pset_name", "")),
                                    "values": dict(command.get("values", {}) or {}),
                                },
                                description=str(command.get("description", "")) or f"Execute {command.get('action_id', '')}",
                            )

                save_mode = self._save_mode if self._save_mode in ("none", "new", "overwrite") else "new"
                saved = False
                saved_path = ""
                save_error = ""

                if save_mode != "none":
                    if not self._source_file:
                        warnings.append("저장 모드가 활성화되었지만 대상 문서가 없어 저장하지 않았습니다.")
                    else:
                        try:
                            hwp = handler._get_hwp()
                            if save_mode == "overwrite":
                                saved_path = str(self._source_file)
                            else:
                                if self._output_path:
                                    target = Path(self._output_path)
                                    target.parent.mkdir(parents=True, exist_ok=True)
                                    if target.exists():
                                        ext = target.suffix.lstrip(".")
                                        saved_path = resolve_output_path(
                                            str(target.parent),
                                            str(target),
                                            new_ext=ext if ext else None,
                                        )
                                    else:
                                        saved_path = str(target)
                                else:
                                    settings = get_settings_manager()
                                    default_output_dir = str(settings.get("default_output_dir", "") or "").strip()
                                    base_dir = Path(default_output_dir) if default_output_dir else Path(self._source_file).parent
                                    save_dir = ensure_dir(str(base_dir / "action_console"))
                                    saved_path = resolve_output_path(
                                        save_dir,
                                        self._source_file,
                                        new_ext="hwp",
                                        suffix="_edited",
                                    )

                            hwp.save_as(saved_path)
                            saved = True
                        except Exception as e:
                            save_error = str(e)
                            warnings.append(f"저장 실패: {e}")

                artifacts["saved"] = saved
                artifacts["saved_path"] = saved_path
                artifacts["save_mode"] = save_mode
                op.warnings = warnings
                op.artifacts = artifacts
                if save_error and not op.error:
                    op.error = save_error
                if save_error:
                    op.success = False

            self.state = WorkerState.FINISHED if op.success else WorkerState.ERROR
            if not op.success and op.error:
                self.error_occurred.emit(op.error)
            failed = int(len((op.artifacts or {}).get("failed_commands", [])))
            if str((op.artifacts or {}).get("save_mode", "")).lower() != "none" and not bool((op.artifacts or {}).get("saved", True)):
                failed += 1
            success_count = max(0, len(normalized) - failed)
            self._emit_finished_once(WorkerResult(
                success=op.success,
                error_message=op.error,
                data=make_summary_data(
                    cancelled=False,
                    success_count=success_count,
                    fail_count=failed,
                    warnings=op.warnings,
                    changed_count=op.changed_count,
                    artifacts=op.artifacts,
                ),
            ))
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(WorkerResult(
                success=False,
                error_message=str(e),
                data=make_summary_data(cancelled=False, success_count=0, fail_count=1),
            ))


class MacroRunWorker(BaseWorker):
    """매크로 실행 작업자."""

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


