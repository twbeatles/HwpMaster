from __future__ import annotations

from itertools import chain
from pathlib import Path
from typing import Any, Iterator, Optional

from .base import BaseWorker, WorkerResult, WorkerState, worker_com_context
from ..output_paths import ensure_dir, resolve_output_path


class ConversionWorker(BaseWorker):
    """문서 변환 작업자."""

    def __init__(
        self,
        files: list[str],
        target_format: str,
        output_dir: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._target_format = target_format
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.hwp_handler import ConvertFormat, HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("변환 준비 중...")

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
            with worker_com_context(), HwpHandler() as handler:
                total = len(self._files)

                out_dir: Optional[str] = None
                if self._output_dir:
                    out_dir = ensure_dir(self._output_dir)

                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(
                            WorkerResult(
                                success=False,
                                error_message="사용자가 작업을 취소했습니다.",
                                data={
                                    "cancelled": True,
                                    "success_count": success_count,
                                    "fail_count": fail_count,
                                    "results": results,
                                },
                            )
                        )
                        return

                    filename = Path(file_path).name
                    self.progress.emit(idx, total, filename)
                    self.status_changed.emit(f"변환 중: {filename}")

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
            self._emit_finished_once(
                WorkerResult(
                    success=(fail_count == 0) and not self.is_cancelled(),
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "results": results,
                    },
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "results": results,
                    },
                )
            )


class MergeWorker(BaseWorker):
    """문서 병합 작업자."""

    def __init__(self, files: list[str], output_path: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._output_path = output_path

    def run(self) -> None:
        from ...core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("병합 준비 중...")
        result = None

        try:
            with worker_com_context(), HwpHandler() as handler:

                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"병합 중: {name}")

                result = handler.merge_files(
                    self._files,
                    self._output_path,
                    progress_callback=progress_cb,
                )

            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=bool(result and result.success),
                    data={
                        "cancelled": False,
                        "success_count": 1 if result and result.success else 0,
                        "fail_count": 0 if result and result.success else 1,
                        "result": result,
                    },
                    error_message=result.error_message if result is not None else None,
                )
            )
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={"cancelled": True, "success_count": 0, "fail_count": 0},
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                )
            )


class DataInjectWorker(BaseWorker):
    """데이터 주입 작업자."""

    def __init__(
        self,
        template_path: str,
        data_file: str,
        output_dir: str,
        filename_field: Optional[str] = None,
        filename_template: Optional[str] = None,
        parent=None,
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
        from ...core.excel_handler import ExcelHandler

        for chunk in ExcelHandler.read_excel_streaming(str(data_path), chunk_size=200):
            for row in chunk:
                yield {str(k): "" if v is None else str(v) for k, v in row.items()}

    def run(self) -> None:
        from ...core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("데이터 주입 준비 중...")

        success_count = 0
        fail_count = 0
        skipped_empty_rows = 0
        filename_collisions = 0
        out_dir = ""

        try:
            self.status_changed.emit("데이터 파일 확인 중...")
            data_path = Path(self._data_file)
            if not data_path.exists():
                self.state = WorkerState.ERROR
                self._emit_finished_once(
                    WorkerResult(
                        success=False,
                        error_message=f"데이터 파일이 존재하지 않습니다: {self._data_file}",
                        data={"cancelled": False, "success_count": 0, "fail_count": 1},
                    )
                )
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
                self._emit_finished_once(
                    WorkerResult(
                        success=False,
                        error_message="데이터 파일이 비어 있습니다.",
                        data={"cancelled": False, "success_count": 0, "fail_count": 1},
                    )
                )
                return

            all_rows = chain([first_row], row_iter)

            with worker_com_context(), HwpHandler() as handler:
                out_dir = ensure_dir(self._output_dir)
                merge_stats: dict[str, int] = {}

                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    shown_total = total_rows if total_rows > 0 else total
                    self.progress.emit(current, shown_total, name)
                    self.status_changed.emit(f"생성 중: {current}/{shown_total if shown_total > 0 else '?'}")

                for result in handler.iter_inject_data(
                    template_path=self._template_path,
                    data_iterable=all_rows,
                    output_dir=out_dir,
                    filename_field=self._filename_field,
                    filename_template=self._filename_template,
                    progress_callback=progress_cb,
                    total_count=total_rows if total_rows > 0 else None,
                    stats=merge_stats,
                ):
                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1

                filename_collisions = int(merge_stats.get("filename_collisions", 0) or 0)

            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=fail_count == 0,
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "output_dir": out_dir,
                        "skipped_empty_rows": skipped_empty_rows,
                        "filename_collisions": filename_collisions,
                    },
                )
            )
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={
                        "cancelled": True,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "skipped_empty_rows": skipped_empty_rows,
                        "filename_collisions": filename_collisions,
                    },
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "skipped_empty_rows": skipped_empty_rows,
                        "filename_collisions": filename_collisions,
                    },
                )
            )


class MetadataCleanWorker(BaseWorker):
    """메타정보 정리 작업자."""

    def __init__(
        self,
        files: list[str],
        output_dir: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._options = options

    def run(self) -> None:
        from ...core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("메타정보 정리 준비 중...")

        success_count = 0
        fail_count = 0
        pii_total = 0
        warnings: list[str] = []
        password_requested = bool(str((self._options or {}).get("document_password", "")).strip())
        password_not_applied = 0

        try:
            with worker_com_context(), HwpHandler() as handler:
                total = len(self._files)

                out_dir: Optional[str] = None
                if self._output_dir:
                    out_dir = ensure_dir(self._output_dir)

                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(
                            WorkerResult(
                                success=False,
                                error_message="사용자가 작업을 취소했습니다.",
                                data={
                                    "cancelled": True,
                                    "success_count": success_count,
                                    "fail_count": fail_count,
                                },
                            )
                        )
                        return

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
            self._emit_finished_once(
                WorkerResult(
                    success=fail_count == 0,
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "pii_total": pii_total,
                        "password_not_applied": password_not_applied,
                        "warnings": warnings,
                    },
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
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
                )
            )


class SplitWorker(BaseWorker):
    """문서 분할 작업자."""

    def __init__(self, file_path: str, page_ranges: list[str], output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._file_path = file_path
        self._page_ranges = page_ranges
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.hwp_handler import HwpHandler

        self.state = WorkerState.RUNNING
        self.status_changed.emit("분할 준비 중...")

        success_count = 0
        fail_count = 0

        try:
            with worker_com_context(), HwpHandler() as handler:

                def progress_cb(current: int, total: int, name: str) -> None:
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"분할 중: {current}/{total}")

                results = handler.split_file(
                    self._file_path,
                    self._page_ranges,
                    self._output_dir,
                    progress_callback=progress_cb,
                )

                for result in results:
                    if result.success:
                        success_count += 1
                    else:
                        fail_count += 1

            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=fail_count == 0,
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                    },
                )
            )
        except InterruptedError as e:
            self.state = WorkerState.CANCELLED
            self.status_changed.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={
                        "cancelled": True,
                        "success_count": success_count,
                        "fail_count": fail_count,
                    },
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                    },
                )
            )
