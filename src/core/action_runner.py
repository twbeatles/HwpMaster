"""
Generic pyhwpx action runner.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .hwp_handler import HwpHandler, OperationResult


@dataclass
class ActionCommand:
    """Single action command."""

    action_type: str  # "run" | "execute"
    action_id: str
    pset_name: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def normalize(self) -> "ActionCommand":
        return ActionCommand(
            action_type=str(self.action_type or "").strip().lower(),
            action_id=str(self.action_id or "").strip(),
            pset_name=str(self.pset_name or "").strip(),
            values=dict(self.values or {}),
            description=str(self.description or "").strip(),
        )


@dataclass
class ActionTemplate:
    """Saved action template."""

    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    commands: list[ActionCommand] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["commands"] = [asdict(cmd) for cmd in self.commands]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionTemplate":
        cmds = [ActionCommand(**raw).normalize() for raw in data.get("commands", [])]
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", datetime.now().isoformat())),
            updated_at=str(data.get("updated_at", datetime.now().isoformat())),
            commands=cmds,
        )


@dataclass
class ActionPreset:
    """Built-in execute-action preset."""

    preset_id: str
    name: str
    category: str
    description: str = ""
    commands: list[ActionCommand] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "commands": [asdict(cmd) for cmd in self.commands],
        }


class ActionRunner:
    """Run pyhwpx actions with template persistence."""

    _BUILTIN_PRESET_RAW: dict[str, dict[str, Any]] = {
        "table_professional_style": {
            "name": "Table Professional Style",
            "category": "table",
            "description": "Apply balanced border/padding/fill values for official reports.",
            "commands": [
                {
                    "action_type": "execute",
                    "action_id": "CellBorder",
                    "pset_name": "HCellBorderFill",
                    "values": {
                        "BorderWidthLeft": 20,
                        "BorderWidthRight": 20,
                        "BorderWidthTop": 20,
                        "BorderWidthBottom": 20,
                        "MarginLeft": 100,
                        "MarginRight": 100,
                        "MarginTop": 60,
                        "MarginBottom": 60,
                    },
                    "description": "Standardize cell border width/padding",
                },
                {
                    "action_type": "execute",
                    "action_id": "CellBorder",
                    "pset_name": "HCellBorderFill",
                    "values": {"FillFaceColor": 15724527},
                    "description": "Set subtle header/background color",
                },
            ],
        },
        "table_dense_grid": {
            "name": "Table Dense Grid",
            "category": "table",
            "description": "Compact grid style for dense tabular documents.",
            "commands": [
                {
                    "action_type": "execute",
                    "action_id": "CellBorder",
                    "pset_name": "HCellBorderFill",
                    "values": {
                        "BorderWidthLeft": 12,
                        "BorderWidthRight": 12,
                        "BorderWidthTop": 12,
                        "BorderWidthBottom": 12,
                        "MarginLeft": 60,
                        "MarginRight": 60,
                        "MarginTop": 40,
                        "MarginBottom": 40,
                    },
                    "description": "Apply compact border/padding set",
                },
            ],
        },
        "shape_presentation_emphasis": {
            "name": "Shape Presentation Emphasis",
            "category": "shape",
            "description": "Set shape shadow/position style for title callouts.",
            "commands": [
                {
                    "action_type": "execute",
                    "action_id": "ShapeObjDialog",
                    "pset_name": "HShapeObject",
                    "values": {
                        "ShadowType": 1,
                        "ShadowXOffset": 120,
                        "ShadowYOffset": 120,
                        "TreatAsChar": 0,
                    },
                    "description": "Apply shape shadow and floating layout",
                },
            ],
        },
        "image_print_enhance": {
            "name": "Image Print Enhance",
            "category": "image",
            "description": "Tune image effect values for print output readability.",
            "commands": [
                {
                    "action_type": "execute",
                    "action_id": "PictureEffect",
                    "pset_name": "HPictureEffect",
                    "values": {"Brightness": 8, "Contrast": 12, "Saturation": -5},
                    "description": "Adjust brightness/contrast/saturation",
                },
                {
                    "action_type": "execute",
                    "action_id": "ShapeObjDialog",
                    "pset_name": "HShapeObject",
                    "values": {"Transparency": 10},
                    "description": "Apply low transparency to avoid over-ink",
                },
            ],
        },
        "image_watermark_light": {
            "name": "Image Watermark Light",
            "category": "image",
            "description": "Apply watermark-like transparency profile to selected image.",
            "commands": [
                {
                    "action_type": "execute",
                    "action_id": "PictureEffect",
                    "pset_name": "HPictureEffect",
                    "values": {"Brightness": 25, "Contrast": -10, "Saturation": -30},
                    "description": "Fade colors for watermark feel",
                },
                {
                    "action_type": "execute",
                    "action_id": "ShapeObjDialog",
                    "pset_name": "HShapeObject",
                    "values": {"Transparency": 55},
                    "description": "Increase transparency",
                },
            ],
        },
    }

    def __init__(self, template_dir: Optional[str] = None) -> None:
        self._logger = logging.getLogger(__name__)
        self._template_dir = Path(template_dir) if template_dir else (Path.home() / ".hwp_master" / "actions")
        self._template_dir.mkdir(parents=True, exist_ok=True)
        self._template_file = self._template_dir / "action_templates.json"
        self._templates: dict[str, ActionTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if not self._template_file.exists():
            return
        try:
            raw = json.loads(self._template_file.read_text(encoding="utf-8"))
            self._templates = {}
            for item in raw.get("templates", []):
                tpl = ActionTemplate.from_dict(item)
                if tpl.name:
                    self._templates[tpl.name] = tpl
        except Exception as e:
            self._logger.warning(f"액션 템플릿 로드 실패: {e}")
            self._templates = {}

    def _save_templates(self) -> None:
        payload = {"version": "1.0", "templates": [tpl.to_dict() for tpl in self._templates.values()]}
        self._template_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_templates(self) -> list[ActionTemplate]:
        return list(self._templates.values())

    def get_template(self, name: str) -> Optional[ActionTemplate]:
        return self._templates.get(name)

    def save_template(self, name: str, commands: list[ActionCommand], description: str = "") -> bool:
        template_name = str(name or "").strip()
        if not template_name:
            return False
        normalized = [cmd.normalize() for cmd in commands]
        now = datetime.now().isoformat()
        created_at = self._templates.get(template_name).created_at if template_name in self._templates else now
        self._templates[template_name] = ActionTemplate(
            name=template_name,
            description=description,
            created_at=created_at,
            updated_at=now,
            commands=normalized,
        )
        self._save_templates()
        return True

    def delete_template(self, name: str) -> bool:
        if name in self._templates:
            del self._templates[name]
            self._save_templates()
            return True
        return False

    @classmethod
    def _build_builtin_presets(cls) -> dict[str, ActionPreset]:
        presets: dict[str, ActionPreset] = {}
        for preset_id, raw in cls._BUILTIN_PRESET_RAW.items():
            commands = [
                ActionCommand(
                    action_type=str(item.get("action_type", "execute")),
                    action_id=str(item.get("action_id", "")),
                    pset_name=str(item.get("pset_name", "")),
                    values=dict(item.get("values", {}) or {}),
                    description=str(item.get("description", "")),
                ).normalize()
                for item in list(raw.get("commands", []))
            ]
            presets[preset_id] = ActionPreset(
                preset_id=preset_id,
                name=str(raw.get("name", preset_id)),
                category=str(raw.get("category", "other")),
                description=str(raw.get("description", "")),
                commands=commands,
            )
        return presets

    def list_builtin_presets(self, category: Optional[str] = None) -> list[ActionPreset]:
        presets = list(self._build_builtin_presets().values())
        if category:
            wanted = str(category).strip().lower()
            presets = [p for p in presets if p.category.lower() == wanted]
        return sorted(presets, key=lambda p: (p.category.lower(), p.name.lower()))

    def get_builtin_preset(self, preset_id: str) -> Optional[ActionPreset]:
        key = str(preset_id or "").strip()
        if not key:
            return None
        return self._build_builtin_presets().get(key)

    def build_builtin_preset_commands(
        self,
        preset_id: str,
        *,
        value_overrides: Optional[dict[str, dict[str, Any]]] = None,
    ) -> list[ActionCommand]:
        """
        Build executable commands from a built-in preset.

        value_overrides:
            - key '#<index>' (0-based) to override a specific command
            - key '<action_id>' to override all commands with that action id
        """
        preset = self.get_builtin_preset(preset_id)
        if preset is None:
            return []

        overrides = value_overrides or {}
        built: list[ActionCommand] = []
        for idx, cmd in enumerate(preset.commands):
            values = dict(cmd.values or {})
            index_key = f"#{idx}"
            if isinstance(overrides.get(index_key), dict):
                values.update(dict(overrides[index_key]))
            if isinstance(overrides.get(cmd.action_id), dict):
                values.update(dict(overrides[cmd.action_id]))
            built.append(
                ActionCommand(
                    action_type=cmd.action_type,
                    action_id=cmd.action_id,
                    pset_name=cmd.pset_name,
                    values=values,
                    description=cmd.description,
                ).normalize()
            )
        return built

    def run_builtin_preset(
        self,
        preset_id: str,
        *,
        stop_on_error: bool = True,
        value_overrides: Optional[dict[str, dict[str, Any]]] = None,
        handler: Optional[HwpHandler] = None,
    ) -> OperationResult:
        commands = self.build_builtin_preset_commands(preset_id, value_overrides=value_overrides)
        if not commands:
            return OperationResult(success=False, error=f"지원하지 않는 프리셋: {preset_id}")
        return self.run_commands(commands, stop_on_error=stop_on_error, handler=handler)

    def run_action(self, action_id: str, handler: Optional[HwpHandler] = None) -> OperationResult:
        try:
            if handler is None:
                with HwpHandler() as owned:
                    ok = owned.run_action(action_id)
            else:
                ok = handler.run_action(action_id)
            return OperationResult(success=ok, changed_count=1 if ok else 0)
        except Exception as e:
            return OperationResult(success=False, error=str(e))

    def execute_action(
        self,
        action_id: str,
        pset_name: str,
        values: dict[str, Any],
        handler: Optional[HwpHandler] = None,
    ) -> OperationResult:
        try:
            if handler is None:
                with HwpHandler() as owned:
                    ok = owned.execute_action(action_id, pset_name, values)
            else:
                ok = handler.execute_action(action_id, pset_name, values)
            return OperationResult(success=ok, changed_count=1 if ok else 0)
        except Exception as e:
            return OperationResult(success=False, error=str(e))

    def run_commands(
        self,
        commands: list[ActionCommand],
        *,
        stop_on_error: bool = True,
        handler: Optional[HwpHandler] = None,
    ) -> OperationResult:
        warnings: list[str] = []
        changed_count = 0
        failed_commands: list[dict[str, Any]] = []
        executed: list[dict[str, Any]] = []

        def _run_one(h: HwpHandler, cmd: ActionCommand) -> OperationResult:
            normalized = cmd.normalize()
            if normalized.action_type == "run":
                return self.run_action(normalized.action_id, handler=h)
            if normalized.action_type == "execute":
                return self.execute_action(normalized.action_id, normalized.pset_name, normalized.values, handler=h)
            return OperationResult(success=False, error=f"지원하지 않는 action_type: {normalized.action_type}")

        try:
            if handler is None:
                with HwpHandler() as owned:
                    for raw in commands:
                        result = _run_one(owned, raw)
                        normalized = raw.normalize()
                        executed.append(asdict(normalized))
                        if result.success:
                            changed_count += max(1, int(result.changed_count or 0))
                        else:
                            failed_commands.append(
                                {"command": asdict(normalized), "error": result.error or "unknown error"}
                            )
                            warnings.append(f"{normalized.action_type}:{normalized.action_id} 실패")
                            if stop_on_error:
                                break
            else:
                for raw in commands:
                    result = _run_one(handler, raw)
                    normalized = raw.normalize()
                    executed.append(asdict(normalized))
                    if result.success:
                        changed_count += max(1, int(result.changed_count or 0))
                    else:
                        failed_commands.append({"command": asdict(normalized), "error": result.error or "unknown error"})
                        warnings.append(f"{normalized.action_type}:{normalized.action_id} 실패")
                        if stop_on_error:
                            break

            success = len(failed_commands) == 0
            return OperationResult(
                success=success,
                warnings=warnings,
                changed_count=changed_count,
                artifacts={"executed": executed, "failed_commands": failed_commands},
                error=failed_commands[0]["error"] if failed_commands else None,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                warnings=warnings,
                changed_count=changed_count,
                artifacts={"executed": executed, "failed_commands": failed_commands},
                error=str(e),
            )

    def run_template(
        self,
        name: str,
        *,
        stop_on_error: bool = True,
        handler: Optional[HwpHandler] = None,
    ) -> OperationResult:
        template = self.get_template(name)
        if template is None:
            return OperationResult(success=False, error=f"템플릿을 찾을 수 없습니다: {name}")
        return self.run_commands(template.commands, stop_on_error=stop_on_error, handler=handler)
