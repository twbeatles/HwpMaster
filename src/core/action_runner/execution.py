from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional

from ..hwp_handler import HwpHandler, OperationResult
from .catalog import build_builtin_preset_commands
from .models import ActionCommand, ActionHandler


def run_builtin_preset(
    runner: Any,
    preset_id: str,
    *,
    stop_on_error: bool = True,
    value_overrides: Optional[dict[str, dict[str, Any]]] = None,
    handler: Optional[ActionHandler] = None,
) -> OperationResult:
    commands = build_builtin_preset_commands(preset_id, value_overrides=value_overrides)
    if not commands:
        return OperationResult(success=False, error=f"지원하지 않는 프리셋: {preset_id}")
    return run_commands(runner, commands, stop_on_error=stop_on_error, handler=handler)


def run_action(
    runner: Any,
    action_id: str,
    handler: Optional[ActionHandler] = None,
) -> OperationResult:
    try:
        ok = False
        if handler is None:
            with HwpHandler() as owned:
                ok = owned.run_action(action_id)
        else:
            ok = handler.run_action(action_id)
        return OperationResult(success=ok, changed_count=1 if ok else 0)
    except Exception as e:
        return OperationResult(success=False, error=str(e))


def execute_action(
    runner: Any,
    action_id: str,
    pset_name: str,
    values: dict[str, Any],
    handler: Optional[ActionHandler] = None,
) -> OperationResult:
    try:
        ok = False
        if handler is None:
            with HwpHandler() as owned:
                ok = owned.execute_action(action_id, pset_name, values)
        else:
            ok = handler.execute_action(action_id, pset_name, values)
        return OperationResult(success=ok, changed_count=1 if ok else 0)
    except Exception as e:
        return OperationResult(success=False, error=str(e))


def run_commands(
    runner: Any,
    commands: list[ActionCommand],
    *,
    stop_on_error: bool = True,
    handler: Optional[ActionHandler] = None,
) -> OperationResult:
    warnings: list[str] = []
    changed_count = 0
    failed_commands: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    succeeded_commands: list[dict[str, Any]] = []

    def _run_one(bound_handler: ActionHandler, cmd: ActionCommand) -> OperationResult:
        normalized = cmd.normalize()
        if normalized.action_type == "run":
            return run_action(runner, normalized.action_id, handler=bound_handler)
        if normalized.action_type == "execute":
            return execute_action(
                runner,
                normalized.action_id,
                normalized.pset_name,
                normalized.values,
                handler=bound_handler,
            )
        return OperationResult(success=False, error=f"지원하지 않는 action_type: {normalized.action_type}")

    try:
        if handler is None:
            with HwpHandler() as owned:
                for raw in commands:
                    result = _run_one(owned, raw)
                    normalized = raw.normalize()
                    normalized_dict = asdict(normalized)
                    executed.append(normalized_dict)
                    if result.success:
                        changed_count += max(1, int(result.changed_count or 0))
                        succeeded_commands.append(normalized_dict)
                    else:
                        failed_commands.append(
                            {"command": normalized_dict, "error": result.error or "unknown error"}
                        )
                        warnings.append(f"{normalized.action_type}:{normalized.action_id} 실패")
                        if stop_on_error:
                            break
        else:
            for raw in commands:
                result = _run_one(handler, raw)
                normalized = raw.normalize()
                normalized_dict = asdict(normalized)
                executed.append(normalized_dict)
                if result.success:
                    changed_count += max(1, int(result.changed_count or 0))
                    succeeded_commands.append(normalized_dict)
                else:
                    failed_commands.append({"command": normalized_dict, "error": result.error or "unknown error"})
                    warnings.append(f"{normalized.action_type}:{normalized.action_id} 실패")
                    if stop_on_error:
                        break

        success = len(failed_commands) == 0
        return OperationResult(
            success=success,
            warnings=warnings,
            changed_count=changed_count,
            artifacts={
                "executed": executed,
                "succeeded_commands": succeeded_commands,
                "failed_commands": failed_commands,
            },
            error=failed_commands[0]["error"] if failed_commands else None,
        )
    except Exception as e:
        return OperationResult(
            success=False,
            warnings=warnings,
            changed_count=changed_count,
            artifacts={
                "executed": executed,
                "succeeded_commands": succeeded_commands,
                "failed_commands": failed_commands,
            },
            error=str(e),
        )


def run_template(
    runner: Any,
    name: str,
    *,
    stop_on_error: bool = True,
    handler: Optional[ActionHandler] = None,
) -> OperationResult:
    template = runner.get_template(name)
    if template is None:
        return OperationResult(success=False, error=f"템플릿을 찾을 수 없습니다: {name}")
    return run_commands(runner, template.commands, stop_on_error=stop_on_error, handler=handler)
