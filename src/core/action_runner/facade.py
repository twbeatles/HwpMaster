from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from .catalog import (
    BUILTIN_PRESET_RAW,
    build_builtin_presets,
    build_builtin_preset_commands,
    get_builtin_preset,
    list_builtin_presets,
)
from .execution import execute_action, run_action, run_builtin_preset, run_commands, run_template
from .models import ActionCommand, ActionHandler, ActionPreset, ActionTemplate
from .storage import delete_template, get_template, list_templates, load_templates, save_template, save_templates


class ActionRunner:
    """Run pyhwpx actions with template persistence."""

    _BUILTIN_PRESET_RAW: dict[str, dict[str, Any]] = BUILTIN_PRESET_RAW

    def __init__(self, template_dir: Optional[str] = None) -> None:
        self._logger = logging.getLogger(__name__)
        self._template_dir = Path(template_dir) if template_dir else (Path.home() / ".hwp_master" / "actions")
        self._template_dir.mkdir(parents=True, exist_ok=True)
        self._template_file = self._template_dir / "action_templates.json"
        self._templates: dict[str, ActionTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        load_templates(self)

    def _save_templates(self) -> None:
        save_templates(self)

    def list_templates(self) -> list[ActionTemplate]:
        return list_templates(self)

    def get_template(self, name: str) -> Optional[ActionTemplate]:
        return get_template(self, name)

    def save_template(self, name: str, commands: list[ActionCommand], description: str = "") -> bool:
        return save_template(self, name, commands, description)

    def delete_template(self, name: str) -> bool:
        return delete_template(self, name)

    @classmethod
    def _build_builtin_presets(cls) -> dict[str, ActionPreset]:
        return build_builtin_presets()

    def list_builtin_presets(self, category: Optional[str] = None) -> list[ActionPreset]:
        return list_builtin_presets(category)

    def get_builtin_preset(self, preset_id: str) -> Optional[ActionPreset]:
        return get_builtin_preset(preset_id)

    def build_builtin_preset_commands(
        self,
        preset_id: str,
        *,
        value_overrides: Optional[dict[str, dict[str, Any]]] = None,
    ) -> list[ActionCommand]:
        return build_builtin_preset_commands(preset_id, value_overrides=value_overrides)

    def run_builtin_preset(
        self,
        preset_id: str,
        *,
        stop_on_error: bool = True,
        value_overrides: Optional[dict[str, dict[str, Any]]] = None,
        handler: Optional[ActionHandler] = None,
    ):
        return run_builtin_preset(
            self,
            preset_id,
            stop_on_error=stop_on_error,
            value_overrides=value_overrides,
            handler=handler,
        )

    def run_action(self, action_id: str, handler: Optional[ActionHandler] = None):
        return run_action(self, action_id, handler=handler)

    def execute_action(
        self,
        action_id: str,
        pset_name: str,
        values: dict[str, Any],
        handler: Optional[ActionHandler] = None,
    ):
        return execute_action(self, action_id, pset_name, values, handler=handler)

    def run_commands(
        self,
        commands: list[ActionCommand],
        *,
        stop_on_error: bool = True,
        handler: Optional[ActionHandler] = None,
    ):
        return run_commands(self, commands, stop_on_error=stop_on_error, handler=handler)

    def run_template(
        self,
        name: str,
        *,
        stop_on_error: bool = True,
        handler: Optional[ActionHandler] = None,
    ):
        return run_template(self, name, stop_on_error=stop_on_error, handler=handler)
