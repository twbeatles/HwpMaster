from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .base import BaseWorker, WorkerResult, WorkerState, _build_failed_summary, worker_com_context
from ..output_paths import ensure_dir, resolve_output_path

if TYPE_CHECKING:
    from ...core.header_footer_manager import HeaderFooterConfig
    from ...core.watermark_manager import WatermarkConfig


class ImageExtractWorker(BaseWorker):
    """이미지 추출 작업자."""

    def __init__(self, files: list[str], output_dir: str, prefix: str = "", parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._prefix = prefix

    def run(self) -> None:
        from ...core.image_extractor import ImageExtractor

        self.state = WorkerState.RUNNING
        self.status_changed.emit("이미지 추출 준비 중...")

        success_count = 0
        fail_count = 0
        total_images = 0
        collected: list[tuple[str, str]] = []

        try:
            with worker_com_context(), ImageExtractor() as extractor:
                total = len(self._files)

                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self.status_changed.emit("작업이 취소되었습니다.")
                        self._emit_finished_once(
                            WorkerResult(
                                success=False,
                                error_message="사용자가 작업을 취소했습니다.",
                                data={
                                    "cancelled": True,
                                    "success_count": success_count,
                                    "fail_count": fail_count,
                                    "total_images": total_images,
                                    "images": collected,
                                },
                            )
                        )
                        return

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
            self._emit_finished_once(
                WorkerResult(
                    success=fail_count == 0,
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "total_images": total_images,
                        "images": collected,
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
                        "total_images": total_images,
                        "images": collected,
                    },
                )
            )


class BookmarkWorker(BaseWorker):
    """북마크 작업자 (삭제/내보내기/추출)."""

    def __init__(
        self,
        mode: str,
        files: list[str],
        output_dir: Optional[str] = None,
        selected_map: Optional[dict[str, list[str]]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._output_dir = output_dir
        self._selected_map = selected_map or {}

    def run(self) -> None:
        from ...core.bookmark_manager import BookmarkManager

        self.state = WorkerState.RUNNING
        self.status_changed.emit("북마크 작업 준비 중...")

        try:
            with worker_com_context(), BookmarkManager() as manager:

                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")

                if self._mode == "delete":
                    results = manager.batch_delete_bookmarks(
                        self._files,
                        self._output_dir,
                        progress_callback=progress_cb,
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
                    data = {"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(results)}
                elif self._mode == "export":
                    if self._output_dir is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(WorkerResult(success=False, error_message="출력 폴더가 필요합니다."))
                        return

                    results = manager.batch_export_bookmarks(
                        self._files,
                        self._output_dir,
                        progress_callback=progress_cb,
                    )
                    success_count = sum(1 for r in results if r.success)
                    fail_count = len(self._files) - success_count
                    data = {"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)}
                else:
                    results = []
                    total = len(self._files)
                    all_bookmarks = []
                    for idx, file_path in enumerate(self._files, start=1):
                        progress_cb(idx, total, file_path)
                        res = manager.get_bookmarks(file_path)
                        results.append(res)
                        if res.success and res.bookmarks:
                            for bookmark in res.bookmarks:
                                all_bookmarks.append((str(file_path), bookmark))

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
            self._emit_finished_once(
                WorkerResult(
                    success=(fail_count == 0),
                    error_message=summary_error,
                    data=data,
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
        from ...core.hyperlink_checker import HyperlinkChecker, LinkInfo

        self.state = WorkerState.RUNNING
        self.status_changed.emit("링크 검사 준비 중...")

        success_count = 0
        fail_count = 0
        total_links = 0
        all_links: list[tuple[str, LinkInfo]] = []
        report_fail_count = 0
        warnings: list[str] = []

        try:
            with worker_com_context(), HyperlinkChecker(
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
                        self._emit_finished_once(
                            WorkerResult(
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
                            )
                        )
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
            self._emit_finished_once(
                WorkerResult(
                    success=fail_count == 0,
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "total_links": total_links,
                        "links": all_links,
                        "report_fail_count": report_fail_count,
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
                        "total_links": total_links,
                        "links": all_links,
                        "report_fail_count": report_fail_count,
                        "warnings": warnings,
                    },
                )
            )


class HeaderFooterWorker(BaseWorker):
    """헤더/푸터 작업자."""

    def __init__(
        self,
        mode: str,
        files: list[str],
        config: Optional["HeaderFooterConfig"] = None,
        output_dir: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._config = config
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.header_footer_manager import HeaderFooterManager

        self.state = WorkerState.RUNNING
        self.status_changed.emit("헤더/푸터 작업 준비 중...")

        try:
            with worker_com_context(), HeaderFooterManager() as manager:

                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")

                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(WorkerResult(success=False, error_message="헤더/푸터 설정이 필요합니다."))
                        return

                    results = manager.batch_apply_header_footer(
                        self._files,
                        self._config,
                        self._output_dir,
                        progress_callback=progress_cb,
                    )
                else:
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
            self._emit_finished_once(
                WorkerResult(
                    success=(fail_count == 0),
                    error_message=summary_error,
                    data={"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)},
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


class WatermarkWorker(BaseWorker):
    """워터마크 작업자."""

    def __init__(
        self,
        mode: str,
        files: list[str],
        config: Optional["WatermarkConfig"] = None,
        output_dir: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._files = files
        self._config = config
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.watermark_manager import WatermarkManager

        self.state = WorkerState.RUNNING
        self.status_changed.emit("워터마크 작업 준비 중...")

        try:
            with worker_com_context(), WatermarkManager() as manager:

                def progress_cb(current, total, name):
                    if self.is_cancelled():
                        raise InterruptedError("작업이 취소되었습니다.")
                    self.progress.emit(current, total, name)
                    self.status_changed.emit(f"처리 중: {name}")

                if self._mode == "apply":
                    if self._config is None:
                        self.state = WorkerState.ERROR
                        self._emit_finished_once(WorkerResult(success=False, error_message="워터마크 설정이 필요합니다."))
                        return

                    results = manager.batch_apply_watermark(
                        self._files,
                        self._config,
                        self._output_dir,
                        progress_callback=progress_cb,
                    )
                else:
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
            self._emit_finished_once(
                WorkerResult(
                    success=(fail_count == 0),
                    error_message=summary_error,
                    data={"cancelled": False, "success_count": success_count, "fail_count": fail_count, "total": len(self._files)},
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


class RegexReplaceWorker(BaseWorker):
    """정규식 치환 작업자."""

    def __init__(self, files: list[str], rules: list[Any], output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._rules = rules
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.regex_replacer import RegexReplacer

        self.state = WorkerState.RUNNING
        out_dir = ensure_dir(self._output_dir)

        success_count = 0
        fail_count = 0
        total_replaced = 0
        total_replaced_known = True
        per_file: dict[str, dict[str, int]] = {}

        try:
            with worker_com_context():
                replacer = RegexReplacer()
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(
                            WorkerResult(
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
                            )
                        )
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
            self._emit_finished_once(
                WorkerResult(
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
                        "total_replaced": total_replaced,
                        "total_replaced_known": total_replaced_known,
                        "results": per_file,
                    },
                )
            )


class StyleCopWorker(BaseWorker):
    """서식 교정 작업자."""

    def __init__(self, files: list[str], rule: Any, output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._rule = rule
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.style_cop import StyleCop

        self.state = WorkerState.RUNNING
        out_dir = ensure_dir(self._output_dir)

        success_count = 0
        fail_count = 0
        results: list[Any] = []

        try:
            with worker_com_context():
                cop = StyleCop()
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
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
            self._emit_finished_once(
                WorkerResult(
                    success=(fail_count == 0),
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "results": results,
                        "output_dir": out_dir,
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


class TableDoctorWorker(BaseWorker):
    """표 교정 작업자."""

    def __init__(self, files: list[str], style: Any, output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._style = style
        self._output_dir = output_dir

    def run(self) -> None:
        from ...core.table_doctor import TableDoctor

        self.state = WorkerState.RUNNING
        out_dir = ensure_dir(self._output_dir)

        success_count = 0
        fail_count = 0
        total_tables_fixed = 0
        results: list[Any] = []

        try:
            with worker_com_context():
                doctor = TableDoctor()
                total = len(self._files)
                for idx, file_path in enumerate(self._files, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(
                            WorkerResult(
                                success=False,
                                error_message="사용자가 작업을 취소했습니다.",
                                data={
                                    "cancelled": True,
                                    "success_count": success_count,
                                    "fail_count": fail_count,
                                    "tables_fixed": total_tables_fixed,
                                    "results": results,
                                },
                            )
                        )
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
            self._emit_finished_once(
                WorkerResult(
                    success=(fail_count == 0),
                    data={
                        "cancelled": False,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "tables_fixed": total_tables_fixed,
                        "results": results,
                        "output_dir": out_dir,
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
                        "tables_fixed": total_tables_fixed,
                        "results": results,
                    },
                )
            )
