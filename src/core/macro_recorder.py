"""
Macro Recorder Module
HWP 매크로 기록 및 재생

Author: HWP Master
"""

import json
import logging
from pathlib import Path
from typing import Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


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
        data["actions"] = [a.to_dict() for a in self.actions]
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroInfo":
        actions = [MacroAction.from_dict(a) for a in data.pop("actions", [])]
        return cls(actions=actions, **data)
    
    def to_python_script(self) -> str:
        """전체 Python 스크립트 생성"""
        lines = [
            '"""',
            f'HWP Master 매크로: {self.name}',
            f'{self.description}',
            f'생성일: {self.created_at}',
            '"""',
            '',
            'import pyhwpx',
            '',
            '',
            'def run_macro():',
            '    """매크로 실행"""',
            '    hwp = pyhwpx.Hwp(visible=True)',
            '    ',
        ]
        
        for action in self.actions:
            code = action.to_python_code()
            lines.append(f'    {code}  # {action.description}' if action.description else f'    {code}')
        
        lines.extend([
            '    ',
            '    print("매크로 실행 완료")',
            '',
            '',
            'if __name__ == "__main__":',
            '    run_macro()',
        ])
        
        return '\n'.join(lines)


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
        """매크로 목록 로드"""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("macros", []):
                        macro = MacroInfo.from_dict(item)
                        self._macros[macro.id] = macro
            except Exception as e:
                self._logger.warning(f"매크로 로드 실패: {e}")
    
    def _save_macros(self) -> None:
        """매크로 목록 저장"""
        data = {
            "version": "1.0",
            "macros": [m.to_dict() for m in self._macros.values()]
        }
        with open(self._metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def is_recording(self) -> bool:
        return self.__class__._global_recording

    @property
    def recorded_action_count(self) -> int:
        return len(self.__class__._global_actions)
    
    def start_recording(self) -> None:
        """녹화 시작"""
        self.__class__._global_recording = True
        self.__class__._global_actions = []
        self._recording = True
        self._current_actions = []
    
    def stop_recording(self) -> list[MacroAction]:
        """녹화 중지 및 액션 반환"""
        self.__class__._global_recording = False
        actions = self.__class__._global_actions.copy()
        self.__class__._global_actions = []
        self._recording = False
        self._current_actions = []
        return actions
    
    def record_action(
        self,
        action_type: str,
        params: Optional[dict[str, Any]] = None,
        description: str = ""
    ) -> None:
        """액션 기록"""
        if self.__class__._global_recording:
            action = MacroAction(
                action_type=action_type,
                params=params or {},
                description=description
            )
            self.__class__._global_actions.append(action)
    
    def save_macro(
        self,
        name: str,
        actions: list[MacroAction],
        description: str = ""
    ) -> MacroInfo:
        """매크로 저장"""
        macro_id = f"macro_{uuid4().hex}"
        
        macro = MacroInfo(
            id=macro_id,
            name=name,
            description=description,
            actions=actions
        )
        
        self._macros[macro_id] = macro
        self._save_macros()
        
        # Python 스크립트 파일 생성
        script_path = self._base_dir / f"{macro_id}.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(macro.to_python_script())
        
        return macro
    
    def get_all_macros(self) -> list[MacroInfo]:
        """모든 매크로 목록"""
        return list(self._macros.values())
    
    def get_macro(self, macro_id: str) -> Optional[MacroInfo]:
        """매크로 조회"""
        return self._macros.get(macro_id)
    
    def delete_macro(self, macro_id: str) -> bool:
        """매크로 삭제"""
        if macro_id in self._macros:
            del self._macros[macro_id]
            self._save_macros()
            
            # 스크립트 파일 삭제
            script_path = self._base_dir / f"{macro_id}.py"
            if script_path.exists():
                script_path.unlink()
            
            return True
        return False
    
    def run_macro(
        self,
        macro_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> bool:
        """
        매크로 실행
        
        Args:
            macro_id: 매크로 ID
            progress_callback: 진행률 콜백
        
        Returns:
            성공 여부
        """
        macro = self._macros.get(macro_id)
        if not macro:
            return False
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                total = len(macro.actions)
                
                for idx, action in enumerate(macro.actions, start=1):
                    if progress_callback:
                        progress_callback(idx, total, action.description or action.action_type)
                    
                    self._execute_action(hwp, action)
                
                # 실행 횟수 증가
                macro.run_count += 1
                macro.modified_at = datetime.now().isoformat()
                self._save_macros()
            
            return True
            
        except Exception as e:
            self._logger.error(f"매크로 실행 오류: {e}", exc_info=True)
            return False
    
    def _execute_action(self, hwp, action: MacroAction) -> None:
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
                # pyhwpx 호환 찾기/바꾸기
                pset = hwp.HParameterSet.HFindReplace
                hwp.HAction.GetDefault("FindReplace", pset.HSet)
                pset.FindString = params.get("find", "")
                pset.ReplaceString = params.get("replace", "")
                pset.ReplaceMode = 1  # 모두 바꾸기
                pset.IgnoreMessage = 1
                hwp.HAction.Execute("FindReplace", pset.HSet)
            elif action_type == "insert_text":
                # pyhwpx 호환 텍스트 삽입
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
                # 보안상 커스텀 코드 실행 비활성화
                self._logger.warning(f"커스텀 액션은 보안상 실행되지 않습니다: {action.description}")
        except Exception as e:
            self._logger.error(f"액션 실행 오류: {action_type} - {e}", exc_info=True)
    
    def export_macro(self, macro_id: str, output_path: str) -> bool:
        """매크로 Python 스크립트 내보내기"""
        macro = self._macros.get(macro_id)
        if not macro:
            return False
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(macro.to_python_script())
            return True
        except Exception as e:
            self._logger.warning(f"매크로 스크립트 저장 실패: {e}")
            return False
    
    def create_quick_macro(
        self,
        name: str,
        find_text: str,
        replace_text: str,
        description: str = ""
    ) -> MacroInfo:
        """빠른 찾기/바꾸기 매크로 생성"""
        actions = [
            MacroAction(
                action_type="find_replace",
                params={"find": find_text, "replace": replace_text},
                description=f"'{find_text}' → '{replace_text}'"
            )
        ]
        return self.save_macro(name, actions, description)
    
    def create_format_macro(
        self,
        name: str,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        color: Optional[str] = None,
        size: Optional[int] = None,
        description: str = ""
    ) -> MacroInfo:
        """서식 변경 매크로 생성"""
        actions = []
        
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
        
        return self.save_macro(name, actions, description)
    
    def create_batch_replace_macro(
        self,
        name: str,
        replacements: list[tuple[str, str]],
        description: str = ""
    ) -> MacroInfo:
        """
        다중 찾기/바꾸기 매크로 생성
        
        Args:
            name: 매크로 이름
            replacements: (찾을 문자열, 바꿀 문자열) 튜플 리스트
            description: 설명
        
        Returns:
            생성된 MacroInfo
        """
        actions = []
        for find_text, replace_text in replacements:
            actions.append(MacroAction(
                action_type="find_replace",
                params={"find": find_text, "replace": replace_text},
                description=f"'{find_text}' → '{replace_text}'"
            ))
        
        if not description:
            description = f"다중 치환 매크로 ({len(replacements)}건)"
        
        return self.save_macro(name, actions, description)
    
    @staticmethod
    def get_preset_macros() -> list[dict[str, Any]]:
        """
        사전 정의된 프리셋 매크로 목록 반환
        
        사용자가 즉시 사용할 수 있는 유용한 매크로 목록입니다.
        """
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
                    ("　", " "),   # 전각 공백
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
                    ("“", "\""),
                    ("”", "\""),
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

