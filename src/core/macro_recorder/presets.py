from __future__ import annotations

from typing import Any, Optional

from .models import MacroAction, MacroInfo


def create_quick_macro(
    recorder: Any,
    name: str,
    find_text: str,
    replace_text: str,
    description: str = "",
) -> MacroInfo:
    actions = [
        MacroAction(
            action_type="find_replace",
            params={"find": find_text, "replace": replace_text},
            description=f"'{find_text}' → '{replace_text}'",
        )
    ]
    return recorder.save_macro(name, actions, description)


def create_format_macro(
    recorder: Any,
    name: str,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    color: Optional[str] = None,
    size: Optional[int] = None,
    description: str = "",
) -> MacroInfo:
    actions: list[MacroAction] = []

    if bold:
        actions.append(MacroAction("set_bold", {"enabled": True}, "굵게"))
    if italic:
        actions.append(MacroAction("set_italic", {"enabled": True}, "기울임"))
    if underline:
        actions.append(MacroAction("set_underline", {"enabled": True}, "밑줄"))
    if color:
        actions.append(MacroAction("set_color", {"color": color}, f"색상: {color}"))
    if size:
        actions.append(MacroAction("set_size", {"size": size}, f"크기: {size}"))

    return recorder.save_macro(name, actions, description)


def create_batch_replace_macro(
    recorder: Any,
    name: str,
    replacements: list[tuple[str, str]],
    description: str = "",
) -> MacroInfo:
    actions: list[MacroAction] = []
    for find_text, replace_text in replacements:
        actions.append(
            MacroAction(
                action_type="find_replace",
                params={"find": find_text, "replace": replace_text},
                description=f"'{find_text}' → '{replace_text}'",
            )
        )

    if not description:
        description = f"다중 치환 매크로 ({len(replacements)}건)"

    return recorder.save_macro(name, actions, description)


def get_preset_macros() -> list[dict[str, Any]]:
    return [
        {
            "name": "공백 정리",
            "description": "연속 공백을 단일 공백으로 변환",
            "replacements": [("  ", " ")],
        },
        {
            "name": "특수문자 통일",
            "description": "전각 문자를 반각으로 통일",
            "replacements": [
                ("　", " "),
                ("，", ","),
                ("．", "."),
                ("：", ":"),
                ("；", ";"),
            ],
        },
        {
            "name": "따옴표 통일",
            "description": "다양한 따옴표를 표준 형식으로 통일",
            "replacements": [
                ("“", '"'),
                ("”", '"'),
                ("‘", "'"),
                ("’", "'"),
            ],
        },
        {
            "name": "줄바꿈 정리",
            "description": "연속 줄바꿈을 단일 줄바꿈으로 정리",
            "replacements": [("\r\n\r\n\r\n", "\r\n\r\n")],
        },
    ]
