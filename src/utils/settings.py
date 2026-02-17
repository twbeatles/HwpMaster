"""
Settings Module
앱 설정 저장/불러오기

Author: HWP Master
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class AppSettings:
    """앱 설정"""

    # 테마
    dark_mode: bool = True
    theme_preset: str = "Dark (기본)"

    # 출력 디렉터리
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

    # 하이퍼링크 검사 설정
    hyperlink_external_requests_enabled: bool = True
    hyperlink_timeout_sec: int = 5
    # comma-separated patterns: "example.com, *.corp.local"
    hyperlink_domain_allowlist: str = ""
    hyperlink_privacy_notice_shown: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class SettingsManager:
    """설정 관리자"""

    def __init__(self, config_dir: Optional[str] = None, save_delay_sec: float = 0.35) -> None:
        self._logger = logging.getLogger(__name__)
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path.home() / ".hwp_master"

        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "settings.json"

        self._save_delay_sec = max(0.05, float(save_delay_sec))
        self._save_lock = threading.Lock()
        self._save_timer: Optional[threading.Timer] = None

        self._settings: AppSettings = AppSettings()
        self.load()
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        """
        누락된 기본값을 보정한다.

        - default_output_dir가 비어있으면 Documents/HWP Master로 설정
        - 디렉터리가 없으면 생성
        """

        changed = False

        if not self._settings.default_output_dir:
            self._settings.default_output_dir = str(Path.home() / "Documents" / "HWP Master")
            changed = True

        try:
            Path(self._settings.default_output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._logger.warning(f"default_output_dir 생성 실패: {self._settings.default_output_dir} ({e})")
            self._settings.default_output_dir = ""
            changed = True

        if changed:
            self.save()

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
            except Exception as e:
                self._logger.warning(f"settings.json 로드 실패(기본값으로 초기화): {self._config_file} ({e})")
                self._settings = AppSettings()

    def _write_settings(self) -> None:
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._logger.warning(f"settings.json 저장 실패: {self._config_file} ({e})")

    def _save_timer_callback(self) -> None:
        with self._save_lock:
            self._save_timer = None
        self._write_settings()

    def save(self, *, immediate: bool = True) -> None:
        """설정 저장.

        Args:
            immediate: True면 즉시 저장, False면 짧게 디바운스 후 저장.
        """
        if immediate:
            with self._save_lock:
                if self._save_timer is not None:
                    self._save_timer.cancel()
                    self._save_timer = None
            self._write_settings()
            return

        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            timer = threading.Timer(self._save_delay_sec, self._save_timer_callback)
            timer.daemon = True
            self._save_timer = timer
            timer.start()

    def flush(self) -> None:
        """디바운스 대기 중인 변경사항을 즉시 저장."""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
        self._write_settings()

    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        return getattr(self._settings, key, default)

    def set(self, key: str, value: Any, *, defer: bool = False) -> None:
        """설정값 변경"""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
            self.save(immediate=not defer)

    def add_recent_file(self, file_path: str) -> None:
        """최근 파일 추가"""
        if file_path in self._settings.recent_files:
            self._settings.recent_files.remove(file_path)

        self._settings.recent_files.insert(0, file_path)

        if len(self._settings.recent_files) > self._settings.max_recent_files:
            self._settings.recent_files = self._settings.recent_files[: self._settings.max_recent_files]

        self.save()

    def get_recent_files(self) -> list[str]:
        """존재하는 최근 파일 목록 반환"""
        existing = [f for f in self._settings.recent_files if Path(f).exists()]

        if len(existing) != len(self._settings.recent_files):
            self._settings.recent_files = existing
            self.save()

        return existing

    def __del__(self) -> None:
        try:
            import builtins

            if not hasattr(builtins, "open"):
                return
            self.flush()
        except Exception:
            pass


# 싱글턴 인스턴스
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """설정 관리자 인스턴스 반환"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
