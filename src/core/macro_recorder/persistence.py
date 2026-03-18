from __future__ import annotations

import json
from typing import Any, Callable, Optional

from .models import MacroAction, MacroInfo


def load_macros(recorder: Any) -> None:
    """매크로 목록 로드"""

    if recorder._metadata_file.exists():
        try:
            with open(recorder._metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("macros", []):
                    macro = MacroInfo.from_dict(item)
                    recorder._macros[macro.id] = macro
        except Exception as e:
            recorder._logger.warning(f"매크로 로드 실패: {e}")


def save_macros(recorder: Any) -> None:
    """매크로 목록 저장"""

    data = {
        "version": "1.0",
        "macros": [macro.to_dict() for macro in recorder._macros.values()],
    }
    with open(recorder._metadata_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def start_recording(recorder: Any) -> None:
    """녹화 시작"""

    recorder.__class__._global_recording = True
    recorder.__class__._global_actions = []
    recorder._recording = True
    recorder._current_actions = []


def stop_recording(recorder: Any) -> list[MacroAction]:
    """녹화 중지 및 액션 반환"""

    recorder.__class__._global_recording = False
    actions = recorder.__class__._global_actions.copy()
    recorder.__class__._global_actions = []
    recorder._recording = False
    recorder._current_actions = []
    return actions


def record_action(
    recorder: Any,
    action_type: str,
    params: Optional[dict[str, Any]] = None,
    description: str = "",
) -> None:
    """액션 기록"""

    if recorder.__class__._global_recording:
        action = MacroAction(
            action_type=action_type,
            params=params or {},
            description=description,
        )
        recorder.__class__._global_actions.append(action)


def save_macro(
    recorder: Any,
    name: str,
    actions: list[MacroAction],
    description: str = "",
) -> MacroInfo:
    """매크로 저장"""

    macro_id = recorder._generate_unique_macro_id()
    macro = MacroInfo(
        id=macro_id,
        name=name,
        description=description,
        actions=actions,
    )

    recorder._macros[macro_id] = macro
    recorder._save_macros()

    script_path = recorder._base_dir / f"{macro_id}.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(macro.to_python_script())

    return macro


def generate_unique_macro_id(recorder: Any) -> str:
    """충돌 없는 매크로 ID 생성."""

    from . import datetime as package_datetime

    for _ in range(32):
        candidate = f"macro_{package_datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        script_path = recorder._base_dir / f"{candidate}.py"
        if candidate not in recorder._macros and not script_path.exists():
            return candidate

    from uuid import uuid4

    while True:
        candidate = f"macro_{package_datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid4().hex[:8]}"
        script_path = recorder._base_dir / f"{candidate}.py"
        if candidate not in recorder._macros and not script_path.exists():
            return candidate


def get_all_macros(recorder: Any) -> list[MacroInfo]:
    return list(recorder._macros.values())


def get_macro(recorder: Any, macro_id: str) -> Optional[MacroInfo]:
    return recorder._macros.get(macro_id)


def delete_macro(recorder: Any, macro_id: str) -> bool:
    if macro_id in recorder._macros:
        del recorder._macros[macro_id]
        recorder._save_macros()

        script_path = recorder._base_dir / f"{macro_id}.py"
        if script_path.exists():
            script_path.unlink()

        return True
    return False


def export_macro(recorder: Any, macro_id: str, output_path: str) -> bool:
    macro = recorder._macros.get(macro_id)
    if not macro:
        return False

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(macro.to_python_script())
        return True
    except Exception as e:
        recorder._logger.warning(f"매크로 스크립트 저장 실패: {e}")
        return False
