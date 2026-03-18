from __future__ import annotations

from .base import BaseWorker, WorkerResult, WorkerState, worker_com_context


class DocDiffWorker(BaseWorker):
    """문서 비교 작업자."""

    def __init__(self, file1: str, file2: str, parent=None) -> None:
        super().__init__(parent)
        self._file1 = file1
        self._file2 = file2

    def run(self) -> None:
        from ...core.doc_diff import DocDiff

        self.state = WorkerState.RUNNING
        self.status_changed.emit("비교 준비 중...")

        try:
            with worker_com_context():
                if self.is_cancelled():
                    self.state = WorkerState.CANCELLED
                    self._emit_finished_once(
                        WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={"cancelled": True, "success_count": 0, "fail_count": 0},
                        )
                    )
                    return

                self.progress.emit(1, 3, "텍스트 추출")
                self.status_changed.emit("텍스트 추출 중...")
                diff = DocDiff()
                result = diff.compare(self._file1, self._file2)

            if self.is_cancelled():
                self.state = WorkerState.CANCELLED
                self._emit_finished_once(
                    WorkerResult(
                        success=False,
                        error_message="사용자가 작업을 취소했습니다.",
                        data={"cancelled": True, "success_count": 0, "fail_count": 0},
                    )
                )
                return

            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=bool(getattr(result, "success", False)),
                    error_message=getattr(result, "error_message", None),
                    data={
                        "cancelled": False,
                        "success_count": 1 if getattr(result, "success", False) else 0,
                        "fail_count": 0 if getattr(result, "success", False) else 1,
                        "result": result,
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
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                )
            )


class SmartTocWorker(BaseWorker):
    """목차 추출 작업자."""

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self._file_path = file_path

    def run(self) -> None:
        from ...core.smart_toc import SmartTOC

        self.state = WorkerState.RUNNING
        self.status_changed.emit("목차 추출 준비 중...")

        try:
            with worker_com_context():
                if self.is_cancelled():
                    self.state = WorkerState.CANCELLED
                    self._emit_finished_once(
                        WorkerResult(
                            success=False,
                            error_message="사용자가 작업을 취소했습니다.",
                            data={"cancelled": True, "success_count": 0, "fail_count": 0},
                        )
                    )
                    return

                self.progress.emit(1, 2, "분석")
                self.status_changed.emit("문서 분석 중...")
                toc = SmartTOC()
                result = toc.extract_toc(self._file_path)

            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=bool(getattr(result, "success", False)),
                    error_message=getattr(result, "error_message", None),
                    data={
                        "cancelled": False,
                        "success_count": 1 if getattr(result, "success", False) else 0,
                        "fail_count": 0 if getattr(result, "success", False) else 1,
                        "result": result,
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
                    data={"cancelled": False, "success_count": 0, "fail_count": 1},
                )
            )
