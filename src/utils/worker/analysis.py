from __future__ import annotations

from pathlib import Path
from uuid import uuid4

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


class EnvironmentDiagnosisWorker(BaseWorker):
    """환경 진단 작업자."""

    def __init__(self, output_dir: str, parent=None) -> None:
        super().__init__(parent)
        self._output_dir = str(output_dir or "").strip()

    @staticmethod
    def _item(name: str, status: str, detail: str) -> dict[str, str]:
        return {
            "name": name,
            "status": status,
            "detail": detail,
        }

    def run(self) -> None:
        self.state = WorkerState.RUNNING
        self.status_changed.emit("환경 진단 준비 중...")

        items: list[dict[str, str]] = []

        try:
            self.progress.emit(1, 4, "pyhwpx import")
            self.status_changed.emit("pyhwpx import 확인 중...")
            pyhwpx_module = None
            try:
                import pyhwpx as imported_pyhwpx

                pyhwpx_module = imported_pyhwpx
                version = str(getattr(imported_pyhwpx, "__version__", "unknown"))
                items.append(self._item("pyhwpx import", "OK", f"pyhwpx import 성공 (version={version})"))
            except Exception as exc:
                items.append(self._item("pyhwpx import", "FAIL", f"pyhwpx import 실패: {exc}"))

            self.progress.emit(2, 4, "COM 초기화")
            self.status_changed.emit("COM 초기화 확인 중...")
            try:
                with worker_com_context():
                    pass
                items.append(self._item("COM 초기화", "OK", "COM 초기화 성공"))
            except Exception as exc:
                items.append(self._item("COM 초기화", "FAIL", f"COM 초기화 실패: {exc}"))

            self.progress.emit(3, 4, "HWP 기동/종료")
            self.status_changed.emit("HWP 기동 확인 중...")
            if pyhwpx_module is None:
                items.append(self._item("HWP 기동/종료", "WARN", "pyhwpx import 실패로 건너뜀"))
            else:
                hwp = None
                try:
                    with worker_com_context():
                        hwp = pyhwpx_module.Hwp(visible=False)
                        hwp.quit()
                    items.append(self._item("HWP 기동/종료", "OK", "HWP 기동 및 종료 성공"))
                except Exception as exc:
                    items.append(self._item("HWP 기동/종료", "FAIL", f"HWP 기동/종료 실패: {exc}"))
                finally:
                    if hwp is not None:
                        try:
                            hwp.quit()
                        except Exception:
                            pass

            self.progress.emit(4, 4, "기본 출력 폴더 쓰기 테스트")
            self.status_changed.emit("출력 폴더 쓰기 테스트 중...")
            try:
                output_dir = Path(self._output_dir).expanduser()
                output_dir.mkdir(parents=True, exist_ok=True)
                probe = output_dir / f".hwp_master_diagnosis_{uuid4().hex}.tmp"
                probe.write_text("diagnosis", encoding="utf-8")
                probe.unlink()
                items.append(
                    self._item(
                        "기본 출력 폴더 쓰기 테스트",
                        "OK",
                        f"출력 폴더 쓰기 가능: {output_dir}",
                    )
                )
            except Exception as exc:
                items.append(
                    self._item(
                        "기본 출력 폴더 쓰기 테스트",
                        "FAIL",
                        f"출력 폴더 쓰기 실패 ({self._output_dir}): {exc}",
                    )
                )

            fail_count = sum(1 for item in items if item["status"] == "FAIL")
            warn_count = sum(1 for item in items if item["status"] == "WARN")
            ok_count = sum(1 for item in items if item["status"] == "OK")
            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=fail_count == 0,
                    data={
                        "cancelled": False,
                        "success_count": ok_count,
                        "fail_count": fail_count,
                        "warn_count": warn_count,
                        "items": items,
                        "summary": f"OK {ok_count} / WARN {warn_count} / FAIL {fail_count}",
                    },
                    error_message=None if fail_count == 0 else "환경 진단에서 실패 항목이 발견되었습니다.",
                )
            )
        except Exception as exc:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(exc))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(exc),
                    data={
                        "cancelled": False,
                        "success_count": 0,
                        "fail_count": 1,
                        "warn_count": 0,
                        "items": items,
                        "summary": "OK 0 / WARN 0 / FAIL 1",
                    },
                )
            )
