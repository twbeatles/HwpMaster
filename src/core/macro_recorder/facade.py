from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from .execution import execute_action, run_macro
from .models import MacroAction, MacroInfo
from .persistence import (
    delete_macro,
    export_macro,
    generate_unique_macro_id,
    get_all_macros,
    get_macro,
    load_macros,
    record_action,
    save_macro,
    save_macros,
    start_recording,
    stop_recording,
)
from .presets import create_batch_replace_macro, create_format_macro, create_quick_macro, get_preset_macros


class MacroRecorder:
    """
    HWP 매크로 레코더
    사용자 조작을 기록하고 재생
    """

    _global_recording: bool = False
    _global_actions: list[MacroAction] = []

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._logger = logging.getLogger(__name__)

        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path.home() / ".hwp_master" / "macros"

        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self._base_dir / "macros.json"

        self._macros: dict[str, MacroInfo] = {}
        self._recording = False
        self._current_actions: list[MacroAction] = []

        self._load_macros()

    def _load_macros(self) -> None:
        load_macros(self)

    def _save_macros(self) -> None:
        save_macros(self)

    @property
    def is_recording(self) -> bool:
        return self.__class__._global_recording

    @property
    def recorded_action_count(self) -> int:
        return len(self.__class__._global_actions)

    def start_recording(self) -> None:
        start_recording(self)

    def stop_recording(self) -> list[MacroAction]:
        return stop_recording(self)

    def record_action(
        self,
        action_type: str,
        params: Optional[dict[str, Any]] = None,
        description: str = "",
    ) -> None:
        record_action(self, action_type, params=params, description=description)

    def save_macro(
        self,
        name: str,
        actions: list[MacroAction],
        description: str = "",
    ) -> MacroInfo:
        return save_macro(self, name, actions, description)

    def _generate_unique_macro_id(self) -> str:
        return generate_unique_macro_id(self)

    def get_all_macros(self) -> list[MacroInfo]:
        return get_all_macros(self)

    def get_macro(self, macro_id: str) -> Optional[MacroInfo]:
        return get_macro(self, macro_id)

    def delete_macro(self, macro_id: str) -> bool:
        return delete_macro(self, macro_id)

    def run_macro(
        self,
        macro_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> bool:
        return run_macro(self, macro_id, progress_callback=progress_callback)

    def _execute_action(self, hwp: Any, action: MacroAction) -> None:
        execute_action(self, hwp, action)

    def export_macro(self, macro_id: str, output_path: str) -> bool:
        return export_macro(self, macro_id, output_path)

    def create_quick_macro(
        self,
        name: str,
        find_text: str,
        replace_text: str,
        description: str = "",
    ) -> MacroInfo:
        return create_quick_macro(self, name, find_text, replace_text, description)

    def create_format_macro(
        self,
        name: str,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        color: Optional[str] = None,
        size: Optional[int] = None,
        description: str = "",
    ) -> MacroInfo:
        return create_format_macro(
            self,
            name,
            bold=bold,
            italic=italic,
            underline=underline,
            color=color,
            size=size,
            description=description,
        )

    def create_batch_replace_macro(
        self,
        name: str,
        replacements: list[tuple[str, str]],
        description: str = "",
    ) -> MacroInfo:
        return create_batch_replace_macro(self, name, replacements, description)

    @staticmethod
    def get_preset_macros() -> list[dict[str, Any]]:
        return get_preset_macros()
