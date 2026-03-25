from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

from .history_manager import HistoryItem, HistoryManager, TaskType, get_history_manager
from .settings import SettingsManager, get_settings_manager


def _coerce_paths(paths: Optional[Iterable[object]]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw in paths or []:
        path = str(raw or "").strip()
        if not path:
            continue
        normalized_path = str(Path(path))
        if normalized_path in seen:
            continue
        seen.add(normalized_path)
        normalized.append(normalized_path)

    return normalized


def _get_settings_manager(settings: Optional[SettingsManager] = None) -> SettingsManager:
    return settings if settings is not None else get_settings_manager()


def _get_history_manager(
    *,
    settings: Optional[SettingsManager] = None,
    history_manager: Optional[HistoryManager] = None,
) -> HistoryManager:
    if history_manager is not None:
        return history_manager
    if settings is not None:
        return get_history_manager(config_dir=settings.config_dir)
    return get_history_manager()


def track_recent_files(paths: Optional[Iterable[object]], *, settings: Optional[SettingsManager] = None) -> list[str]:
    manager = _get_settings_manager(settings)
    normalized = [path for path in _coerce_paths(paths) if Path(path).exists()]

    for path in reversed(normalized):
        manager.add_recent_file(path)

    return normalized


def record_task_summary(
    task_type: TaskType,
    description: str,
    files: Optional[Iterable[object]],
    success_count: int,
    fail_count: int,
    *,
    options: Optional[dict[str, Any]] = None,
    settings: Optional[SettingsManager] = None,
    history_manager: Optional[HistoryManager] = None,
    recent_files: Optional[Iterable[object]] = None,
) -> Optional[HistoryItem]:
    tracked_files = _coerce_paths(files)
    recent_candidates = _coerce_paths(recent_files if recent_files is not None else tracked_files)

    if not description.strip():
        return None

    item = _get_history_manager(settings=settings, history_manager=history_manager).add(
        task_type,
        description,
        tracked_files,
        success_count=max(0, int(success_count)),
        fail_count=max(0, int(fail_count)),
        options=options,
    )
    track_recent_files(recent_candidates, settings=settings)
    return item


def record_task_result(
    task_type: TaskType,
    description: str,
    files: Optional[Iterable[object]],
    result: Any,
    *,
    options: Optional[dict[str, Any]] = None,
    settings: Optional[SettingsManager] = None,
    history_manager: Optional[HistoryManager] = None,
    recent_files: Optional[Iterable[object]] = None,
) -> Optional[HistoryItem]:
    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        data = {}

    if bool(data.get("cancelled")):
        return None

    tracked_files = _coerce_paths(files)
    success_count = int(data.get("success_count", 0) or 0)
    fail_count = int(data.get("fail_count", 0) or 0)

    if success_count == 0 and fail_count == 0:
        if bool(getattr(result, "success", False)):
            success_count = max(1, len(tracked_files))
        else:
            fail_count = max(1, len(tracked_files) or 1)

    return record_task_summary(
        task_type,
        description,
        tracked_files,
        success_count,
        fail_count,
        options=options,
        settings=settings,
        history_manager=history_manager,
        recent_files=recent_files,
    )
