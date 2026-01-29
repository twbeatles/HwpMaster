"""
Settings Module
앱 설정 저장/불러오기

Author: HWP Master
"""

import json
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class AppSettings:
    """앱 설정"""
    # 테마
    dark_mode: bool = True
    theme_preset: str = "Dark (기본)"
    
    # 출력 디렉토리
    default_output_dir: str = ""
    
    # 최근 사용 파일
    recent_files: list[str] = field(default_factory=list)
    max_recent_files: int = 10
    
    # 즐겨찾기 폴더
    favorite_folders: list[str] = field(default_factory=list)
    
    # 변환 설정
    default_convert_format: str = "PDF"
    
    # UI 설정
    sidebar_collapsed: bool = False
    window_width: int = 1400
    window_height: int = 900
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        # 알려진 필드만 추출
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class SettingsManager:
    """설정 관리자"""
    
    def __init__(self, config_dir: Optional[str] = None) -> None:
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path.home() / ".hwp_master"
        
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "settings.json"
        
        self._settings: AppSettings = AppSettings()
        self.load()
    
    @property
    def settings(self) -> AppSettings:
        return self._settings
    
    def load(self) -> None:
        """설정 불러오기"""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._settings = AppSettings.from_dict(data)
            except Exception:
                self._settings = AppSettings()
    
    def save(self) -> None:
        """설정 저장"""
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        return getattr(self._settings, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """설정값 변경"""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
            self.save()
    
    def add_recent_file(self, file_path: str) -> None:
        """최근 파일 추가"""
        if file_path in self._settings.recent_files:
            self._settings.recent_files.remove(file_path)
        
        self._settings.recent_files.insert(0, file_path)
        
        # 최대 개수 유지
        if len(self._settings.recent_files) > self._settings.max_recent_files:
            self._settings.recent_files = self._settings.recent_files[:self._settings.max_recent_files]
        
        self.save()
    
    def get_recent_files(self) -> list[str]:
        """최근 파일 목록"""
        # 존재하는 파일만 반환
        existing = [f for f in self._settings.recent_files if Path(f).exists()]
        
        if len(existing) != len(self._settings.recent_files):
            self._settings.recent_files = existing
            self.save()
        
        return existing


# 싱글톤 인스턴스
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """설정 관리자 인스턴스 반환"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
