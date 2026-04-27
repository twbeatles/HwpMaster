from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ...utils.atomic_write import atomic_write_bytes
from ...utils.filename_sanitizer import sanitize_filename
from .session import EditorSession


@dataclass
class SaveResult:
    success: bool
    path: str = ""
    backup_path: str = ""
    mode: str = ""
    error: Optional[str] = None
    recovery: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "path": self.path,
            "backup_path": self.backup_path,
            "mode": self.mode,
            "error": self.error,
            "recovery": self.recovery,
        }


class EditorSaveService:
    """Save policy for the embedded editor.

    HWP overwrite is allowed after one backup is created. HWPX overwrite stays
    disabled by default until round-trip compatibility is proven.
    """

    def __init__(self, config_dir: str | Path, *, allow_hwpx_overwrite: bool = False) -> None:
        self._config_dir = Path(config_dir)
        self._backup_dir = self._config_dir / "editor_backups"
        self._recovery_dir = self._config_dir / "recovery"
        self._allow_hwpx_overwrite = bool(allow_hwpx_overwrite)

    @property
    def backup_dir(self) -> Path:
        return self._backup_dir

    @property
    def recovery_dir(self) -> Path:
        return self._recovery_dir

    def save(
        self,
        session: EditorSession,
        content: bytes,
        *,
        mode: str = "current",
        output_format: str = "",
        target_path: str = "",
    ) -> SaveResult:
        normalized_mode = str(mode or "current").strip().lower()
        fmt = str(output_format or session.source_format or "hwp").strip().lower().lstrip(".")
        if fmt not in {"hwp", "hwpx"}:
            return SaveResult(success=False, mode=normalized_mode, error=f"지원하지 않는 저장 형식: {fmt}")

        if normalized_mode == "recovery":
            return self._save_recovery(session, bytes(content), fmt)

        if normalized_mode == "save_as":
            if not target_path:
                return SaveResult(success=False, mode=normalized_mode, error="다른 이름 저장 경로가 비어 있습니다.")
            save_path = Path(target_path)
        elif normalized_mode == "current":
            if not session.current_path:
                return SaveResult(success=False, mode=normalized_mode, error="현재 저장 경로가 없습니다.")
            save_path = Path(session.current_path)
            if save_path.suffix.lower() == ".hwpx" and not (session.allow_hwpx_overwrite or self._allow_hwpx_overwrite):
                return SaveResult(
                    success=False,
                    mode=normalized_mode,
                    error="HWPX 직접 덮어쓰기는 아직 비활성화되어 있습니다. 다른 이름 저장을 사용해주세요.",
                )
        else:
            return SaveResult(success=False, mode=normalized_mode, error=f"지원하지 않는 저장 모드: {mode}")

        if save_path.suffix.lower() not in {".hwp", ".hwpx"}:
            save_path = save_path.with_suffix(f".{fmt}")

        backup_path = ""
        try:
            if normalized_mode == "current":
                backup_path = self._ensure_backup(session, save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(save_path, bytes(content))
            session.mark_saved(str(save_path), bytes(content))
            return SaveResult(
                success=True,
                path=str(save_path),
                backup_path=backup_path or session.backup_path,
                mode=normalized_mode,
            )
        except Exception as e:
            return SaveResult(success=False, mode=normalized_mode, error=str(e), backup_path=backup_path)

    def _ensure_backup(self, session: EditorSession, save_path: Path) -> str:
        if session.backup_created and session.backup_path:
            return session.backup_path
        if not save_path.exists():
            session.backup_created = True
            return ""

        self._backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_stem = sanitize_filename(save_path.stem)
        backup_name = f"{safe_stem}_{timestamp}.bak{save_path.suffix.lower() or '.hwp'}"
        backup_path = self._backup_dir / backup_name
        shutil.copy2(save_path, backup_path)
        session.backup_created = True
        session.backup_path = str(backup_path)
        return session.backup_path

    def _save_recovery(self, session: EditorSession, content: bytes, output_format: str) -> SaveResult:
        try:
            self._recovery_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = sanitize_filename(Path(session.current_path or session.source_path).stem or session.session_id)
            path = self._recovery_dir / f"{base}_{session.session_id[:8]}_{timestamp}.{output_format}"
            atomic_write_bytes(path, bytes(content))
            return SaveResult(success=True, path=str(path), mode="recovery", recovery=True)
        except Exception as e:
            return SaveResult(success=False, mode="recovery", recovery=True, error=str(e))
