from __future__ import annotations

from typing import Any, Optional

from .models import ActionCommand, ActionPreset


BUILTIN_PRESET_RAW: dict[str, dict[str, Any]] = {
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


def build_builtin_presets() -> dict[str, ActionPreset]:
    presets: dict[str, ActionPreset] = {}
    for preset_id, raw in BUILTIN_PRESET_RAW.items():
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


def list_builtin_presets(category: Optional[str] = None) -> list[ActionPreset]:
    presets = list(build_builtin_presets().values())
    if category:
        wanted = str(category).strip().lower()
        presets = [preset for preset in presets if preset.category.lower() == wanted]
    return sorted(presets, key=lambda preset: (preset.category.lower(), preset.name.lower()))


def get_builtin_preset(preset_id: str) -> Optional[ActionPreset]:
    key = str(preset_id or "").strip()
    if not key:
        return None
    return build_builtin_presets().get(key)


def build_builtin_preset_commands(
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

    preset = get_builtin_preset(preset_id)
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
