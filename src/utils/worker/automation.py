from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseWorker, WorkerResult, WorkerState, make_summary_data, worker_com_context
from ..output_paths import ensure_dir, resolve_output_path


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
        from ...core.action_runner import ActionCommand, ActionRunner
        from ...core.hwp_handler import HwpHandler
        from ...core.macro_recorder import MacroRecorder
        from ..settings import get_settings_manager

        self.state = WorkerState.RUNNING
        self.status_changed.emit("액션 실행 준비 중...")
        normalized: list[ActionCommand] = []
        op = None

        try:
            with worker_com_context(), HwpHandler() as handler:
                if self._source_file:
                    handler._get_hwp().open(self._source_file)

                total = len(self._commands)
                for idx, raw in enumerate(self._commands, start=1):
                    if self.is_cancelled():
                        self.state = WorkerState.CANCELLED
                        self._emit_finished_once(
                            WorkerResult(
                                success=False,
                                error_message="사용자가 작업을 취소했습니다.",
                                data=make_summary_data(
                                    cancelled=True,
                                    success_count=0,
                                    fail_count=0,
                                    changed_count=idx - 1,
                                ),
                            )
                        )
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
                                params={"action_id": str(command.get("action_id", ""))},
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

            op_success = bool(op and op.success)
            op_error = op.error if op is not None else None
            op_artifacts = op.artifacts if op is not None else {}
            op_warnings = op.warnings if op is not None else []
            op_changed_count = op.changed_count if op is not None else 0

            self.state = WorkerState.FINISHED if op_success else WorkerState.ERROR
            if not op_success and op_error:
                self.error_occurred.emit(op_error)
            failed = int(len((op_artifacts or {}).get("failed_commands", [])))
            if str((op_artifacts or {}).get("save_mode", "")).lower() != "none" and not bool((op_artifacts or {}).get("saved", True)):
                failed += 1
            success_count = max(0, len(normalized) - failed)
            self._emit_finished_once(
                WorkerResult(
                    success=op_success,
                    error_message=op_error,
                    data=make_summary_data(
                        cancelled=False,
                        success_count=success_count,
                        fail_count=failed,
                        warnings=op_warnings,
                        changed_count=op_changed_count,
                        artifacts=op_artifacts,
                    ),
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data=make_summary_data(cancelled=False, success_count=0, fail_count=1),
                )
            )


class MacroRunWorker(BaseWorker):
    """매크로 실행 작업자."""

    def __init__(self, macro_id: str, parent=None) -> None:
        super().__init__(parent)
        self._macro_id = macro_id

    def run(self) -> None:
        from ...core.hwp_handler import HwpHandler
        from ...core.macro_recorder import MacroRecorder

        self.state = WorkerState.RUNNING
        self.status_changed.emit("매크로 실행 준비 중...")

        success_count = 0
        fail_count = 0

        try:
            with worker_com_context(), HwpHandler() as handler:
                recorder = MacroRecorder()
                macro = recorder.get_macro(self._macro_id)
                if not macro:
                    self.state = WorkerState.ERROR
                    self._emit_finished_once(
                        WorkerResult(
                            success=False,
                            error_message="매크로를 찾을 수 없습니다.",
                            data={"cancelled": False, "success_count": 0, "fail_count": 1},
                        )
                    )
                    return

                handler._ensure_hwp()
                hwp = handler._hwp

                total = len(macro.actions)
                for idx, action in enumerate(macro.actions, start=1):
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

                    self.progress.emit(idx, max(total, 1), action.description or action.action_type)
                    self.status_changed.emit(f"실행 중: {action.description or action.action_type}")
                    recorder._execute_action(hwp, action)

                macro.run_count += 1
                macro.modified_at = datetime.now().isoformat()
                recorder._save_macros()

                success_count = 1

            self.state = WorkerState.FINISHED
            self._emit_finished_once(
                WorkerResult(
                    success=True,
                    data={"cancelled": False, "success_count": success_count, "fail_count": fail_count},
                )
            )
        except Exception as e:
            self.state = WorkerState.ERROR
            self.error_occurred.emit(str(e))
            fail_count = 1
            self._emit_finished_once(
                WorkerResult(
                    success=False,
                    error_message=str(e),
                    data={"cancelled": False, "success_count": 0, "fail_count": fail_count},
                )
            )
