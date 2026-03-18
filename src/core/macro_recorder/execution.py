from __future__ import annotations

from typing import Any, Callable, Optional

from .models import MacroAction


def run_macro(
    recorder: Any,
    macro_id: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """매크로 실행"""

    macro = recorder._macros.get(macro_id)
    if not macro:
        return False

    try:
        from . import datetime as package_datetime
        from src.core.hwp_handler import HwpHandler

        with HwpHandler() as handler:
            handler._ensure_hwp()
            hwp = handler._hwp

            total = len(macro.actions)

            for idx, action in enumerate(macro.actions, start=1):
                if progress_callback:
                    progress_callback(idx, total, action.description or action.action_type)

                recorder._execute_action(hwp, action)

            macro.run_count += 1
            macro.modified_at = package_datetime.now().isoformat()
            recorder._save_macros()

        return True
    except Exception as e:
        recorder._logger.error(f"매크로 실행 오류: {e}", exc_info=True)
        return False


def execute_action(recorder: Any, hwp: Any, action: MacroAction) -> None:
    """단일 액션 실행 (pyhwpx 호환)"""

    action_type = action.action_type
    params = action.params

    try:
        if action_type == "run_action":
            action_id = str(params.get("action_id", "")).strip()
            if action_id:
                hwp.Run(action_id)
        elif action_type == "execute_action":
            action_id = str(params.get("action_id", "")).strip()
            pset_name = str(params.get("pset_name", "")).strip()
            values = dict(params.get("values", {}) or {})
            if action_id and pset_name:
                pset = getattr(hwp.HParameterSet, pset_name, None)
                if pset is not None:
                    hwp.HAction.GetDefault(action_id, pset.HSet)
                    for key, value in values.items():
                        if hasattr(pset, str(key)):
                            setattr(pset, str(key), value)
                    hwp.HAction.Execute(action_id, pset.HSet)
        elif action_type == "open_file":
            hwp.open(params.get("path", ""))
        elif action_type == "save_file":
            hwp.save_as(params.get("path", ""))
        elif action_type == "find_replace":
            pset = hwp.HParameterSet.HFindReplace
            hwp.HAction.GetDefault("FindReplace", pset.HSet)
            pset.FindString = params.get("find", "")
            pset.ReplaceString = params.get("replace", "")
            pset.ReplaceMode = 1
            pset.IgnoreMessage = 1
            hwp.HAction.Execute("FindReplace", pset.HSet)
        elif action_type == "insert_text":
            hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
            hwp.HParameterSet.HInsertText.Text = params.get("text", "")
            hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
        elif action_type == "select_all":
            hwp.Run("SelectAll")
        elif action_type == "set_bold":
            hwp.Run("CharShapeBold")
        elif action_type == "set_italic":
            hwp.Run("CharShapeItalic")
        elif action_type == "set_underline":
            hwp.Run("CharShapeUnderline")
        elif action_type == "set_color":
            color = MacroAction._safe_str(params.get("color"), "#000000")
            r, g, b = MacroAction._hex_to_rgb(color)
            hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet)
            hwp.HParameterSet.HCharShape.TextColor = hwp.RGBColor(r, g, b)
            hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)
        elif action_type == "set_size":
            size = float(params.get("size", 10))
            hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet)
            hwp.HParameterSet.HCharShape.Height = hwp.PointToHwpUnit(size)
            hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)
        elif action_type == "format_text":
            font = params.get("font")
            if font:
                hwp.set_font(str(font))
            if "size" in params:
                size = float(params.get("size", 10))
                hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet)
                hwp.HParameterSet.HCharShape.Height = hwp.PointToHwpUnit(size)
                hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)
            if "color" in params:
                color = MacroAction._safe_str(params.get("color"), "#000000")
                r, g, b = MacroAction._hex_to_rgb(color)
                hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet)
                hwp.HParameterSet.HCharShape.TextColor = hwp.RGBColor(r, g, b)
                hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)
            if bool(params.get("bold")):
                hwp.Run("CharShapeBold")
            if bool(params.get("italic")):
                hwp.Run("CharShapeItalic")
            if bool(params.get("underline")):
                hwp.Run("CharShapeUnderline")
        elif action_type == "custom":
            recorder._logger.warning(f"커스텀 액션은 보안상 실행되지 않습니다: {action.description}")
    except Exception as e:
        recorder._logger.error(f"액션 실행 오류: {action_type} - {e}", exc_info=True)
