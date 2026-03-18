from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal


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


def worker_com_context():
    from . import com_context as package_com_context

    return package_com_context()


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

    progress = Signal(int, int, str)
    status_changed = Signal(str)
    finished_with_result = Signal(object)
    error_occurred = Signal(str)

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
        raise NotImplementedError

    def _emit_finished_once(self, result: WorkerResult) -> None:
        with QMutexLocker(self._mutex):
            if self._result_emitted:
                return
            self._result_emitted = True
        self.finished_with_result.emit(result)
