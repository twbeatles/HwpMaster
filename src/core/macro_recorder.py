"""
Macro Recorder Module
HWP 매크로 기록 및 재생

Author: HWP Master
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class MacroActionType(Enum):
    """매크로 액션 타입"""
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
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MacroAction":
        return cls(**data)
    
    def to_python_code(self) -> str:
        """Python 코드로 변환"""
        action = self.action_type
        params = self.params
        
        code_map = {
            "open_file": f'hwp.open("{params.get("path", "")}")',
            "save_file": f'hwp.save_as("{params.get("path", "")}")',
            "find_replace": f'hwp.find_replace("{params.get("find", "")}", "{params.get("replace", "")}")',
            "format_text": f'hwp.format_text({params})',
            "insert_text": f'hwp.insert_text("{params.get("text", "")}")',
            "delete_text": 'hwp.delete_selection()',
            "select_all": 'hwp.select_all()',
            "copy": 'hwp.copy()',
            "paste": 'hwp.paste()',
            "undo": 'hwp.undo()',
            "redo": 'hwp.redo()',
            "set_font": f'hwp.set_font("{params.get("font", "맑은 고딕")}")',
            "set_color": f'hwp.set_text_color("{params.get("color", "#000000")}")',
            "set_size": f'hwp.set_font_size({params.get("size", 10)})',
            "set_bold": f'hwp.set_bold({params.get("enabled", True)})',
            "set_italic": f'hwp.set_italic({params.get("enabled", True)})',
            "set_underline": f'hwp.set_underline({params.get("enabled", True)})',
            "custom": params.get("code", "# Custom action"),
        }
        
        return code_map.get(action, f"# Unknown action: {action}")


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
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["actions"] = [a.to_dict() for a in self.actions]
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "MacroInfo":
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
        return self._recording
    
    def start_recording(self) -> None:
        """녹화 시작"""
        self._recording = True
        self._current_actions = []
    
    def stop_recording(self) -> list[MacroAction]:
        """녹화 중지 및 액션 반환"""
        self._recording = False
        actions = self._current_actions.copy()
        self._current_actions = []
        return actions
    
    def record_action(
        self,
        action_type: str,
        params: Optional[dict] = None,
        description: str = ""
    ) -> None:
        """액션 기록"""
        if self._recording:
            action = MacroAction(
                action_type=action_type,
                params=params or {},
                description=description
            )
            self._current_actions.append(action)
    
    def save_macro(
        self,
        name: str,
        actions: list[MacroAction],
        description: str = ""
    ) -> MacroInfo:
        """매크로 저장"""
        macro_id = f"macro_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
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
        """단일 액션 실행"""
        action_type = action.action_type
        params = action.params
        
        try:
            if action_type == "open_file":
                hwp.open(params.get("path", ""))
            elif action_type == "save_file":
                hwp.save_as(params.get("path", ""))
            elif action_type == "find_replace":
                hwp.find_replace(params.get("find", ""), params.get("replace", ""))
            elif action_type == "insert_text":
                hwp.insert_text(params.get("text", ""))
            elif action_type == "select_all":
                hwp.select_all()
            elif action_type == "set_bold":
                hwp.set_bold(params.get("enabled", True))
            elif action_type == "set_italic":
                hwp.set_italic(params.get("enabled", True))
            elif action_type == "set_underline":
                hwp.set_underline(params.get("enabled", True))
            elif action_type == "set_color":
                hwp.set_text_color(params.get("color", "#000000"))
            elif action_type == "set_size":
                hwp.set_font_size(params.get("size", 10))
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
