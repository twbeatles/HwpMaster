from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MacroActionType(Enum):
    """매크로 액션 타입"""

    RUN_ACTION = "run_action"
    EXECUTE_ACTION = "execute_action"
    OPEN_FILE = "open_file"
    SAVE_FILE = "save_file"
    FIND_REPLACE = "find_replace"
    FORMAT_TEXT = "format_text"
    INSERT_TEXT = "insert_text"
    DELETE_TEXT = "delete_text"
    MOVE_CURSOR = "move_cursor"
    SELECT_ALL = "select_all"
    COPY = "copy"
    PASTE = "paste"
    UNDO = "undo"
    REDO = "redo"
    SET_FONT = "set_font"
    SET_COLOR = "set_color"
    SET_SIZE = "set_size"
    SET_BOLD = "set_bold"
    SET_ITALIC = "set_italic"
    SET_UNDERLINE = "set_underline"
    CUSTOM = "custom"


@dataclass
class MacroAction:
    """매크로 단일 액션"""

    action_type: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroAction":
        return cls(**data)

    @staticmethod
    def _safe_str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _hex_to_rgb(color: str) -> tuple[int, int, int]:
        s = str(color or "").strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) != 6:
            return (0, 0, 0)
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except Exception:
            return (0, 0, 0)

    def to_python_code(self) -> str:
        """Python 코드로 변환"""

        action = self.action_type
        params = self.params
        if action == "run_action":
            action_id = self._safe_str(params.get("action_id"), "")
            return f"hwp.Run({action_id.__repr__()})"
        if action == "execute_action":
            action_id = self._safe_str(params.get("action_id"), "")
            pset_name = self._safe_str(params.get("pset_name"), "")
            values = params.get("values", {}) or {}
            lines = [
                f"pset = hwp.HParameterSet.{pset_name}",
                f'hwp.HAction.GetDefault({action_id.__repr__()}, pset.HSet)',
            ]
            for key, value in values.items():
                lines.append(f"pset.{key} = {value!r}")
            lines.append(f'hwp.HAction.Execute({action_id.__repr__()}, pset.HSet)')
            return " ; ".join(lines)
        if action == "open_file":
            return f"hwp.open({self._safe_str(params.get('path'), '').__repr__()})"
        if action == "save_file":
            return f"hwp.save_as({self._safe_str(params.get('path'), '').__repr__()})"
        if action == "find_replace":
            find_text = self._safe_str(params.get("find"), "")
            replace_text = self._safe_str(params.get("replace"), "")
            return f"hwp.find_replace({find_text.__repr__()}, {replace_text.__repr__()})"
        if action == "insert_text":
            text = self._safe_str(params.get("text"), "")
            return f"hwp.insert_text({text.__repr__()})"
        if action == "delete_text":
            return 'hwp.Run("Delete")'
        if action == "select_all":
            return 'hwp.Run("SelectAll")'
        if action == "copy":
            return 'hwp.Run("Copy")'
        if action == "paste":
            return "hwp.paste()"
        if action == "undo":
            return 'hwp.Run("Undo")'
        if action == "redo":
            return 'hwp.Run("Redo")'
        if action == "set_font":
            font = self._safe_str(params.get("font"), "맑은 고딕")
            return f"hwp.set_font({font.__repr__()})"
        if action == "set_color":
            r, g, b = self._hex_to_rgb(self._safe_str(params.get("color"), "#000000"))
            return (
                'hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet); '
                "hwp.HParameterSet.HCharShape.TextColor = hwp.RGBColor("
                f"{r}, {g}, {b}); "
                'hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)'
            )
        if action == "set_size":
            size = float(params.get("size", 10))
            return (
                'hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet); '
                f"hwp.HParameterSet.HCharShape.Height = hwp.PointToHwpUnit({size}); "
                'hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)'
            )
        if action == "set_bold":
            return 'hwp.Run("CharShapeBold")'
        if action == "set_italic":
            return 'hwp.Run("CharShapeItalic")'
        if action == "set_underline":
            return 'hwp.Run("CharShapeUnderline")'
        if action == "format_text":
            chunks: list[str] = []
            if "font" in params:
                chunks.append(f"hwp.set_font({self._safe_str(params.get('font'), '맑은 고딕').__repr__()})")
            if "size" in params:
                size = float(params.get("size", 10))
                chunks.append(
                    'hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet); '
                    f"hwp.HParameterSet.HCharShape.Height = hwp.PointToHwpUnit({size}); "
                    'hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)'
                )
            if "color" in params:
                r, g, b = self._hex_to_rgb(self._safe_str(params.get("color"), "#000000"))
                chunks.append(
                    'hwp.HAction.GetDefault("CharShape", hwp.HParameterSet.HCharShape.HSet); '
                    "hwp.HParameterSet.HCharShape.TextColor = hwp.RGBColor("
                    f"{r}, {g}, {b}); "
                    'hwp.HAction.Execute("CharShape", hwp.HParameterSet.HCharShape.HSet)'
                )
            if params.get("bold"):
                chunks.append('hwp.Run("CharShapeBold")')
            if params.get("italic"):
                chunks.append('hwp.Run("CharShapeItalic")')
            if params.get("underline"):
                chunks.append('hwp.Run("CharShapeUnderline")')
            return " ; ".join(chunks) if chunks else "# format_text: no-op"
        if action == "custom":
            return self._safe_str(params.get("code"), "# Custom action")
        return f"# Unknown action: {action}"


@dataclass
class MacroInfo:
    """매크로 정보"""

    id: str
    name: str
    description: str
    actions: list[MacroAction]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    run_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["actions"] = [action.to_dict() for action in self.actions]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroInfo":
        actions = [MacroAction.from_dict(action) for action in data.pop("actions", [])]
        return cls(actions=actions, **data)

    def to_python_script(self) -> str:
        """전체 Python 스크립트 생성"""

        lines = [
            '"""',
            f"HWP Master 매크로: {self.name}",
            f"{self.description}",
            f"생성일: {self.created_at}",
            '"""',
            "",
            "import pyhwpx",
            "",
            "",
            "def run_macro():",
            '    """매크로 실행"""',
            "    hwp = pyhwpx.Hwp(visible=True)",
            "    ",
        ]

        for action in self.actions:
            code = action.to_python_code()
            lines.append(f"    {code}  # {action.description}" if action.description else f"    {code}")

        lines.extend(
            [
                "    ",
                '    print("매크로 실행 완료")',
                "",
                "",
                'if __name__ == "__main__":',
                "    run_macro()",
            ]
        )

        return "\n".join(lines)
