from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_EDITOR_SUFFIXES = {".hwp", ".hwpx"}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class EditorSession:
    """State for one document opened in the embedded rhwp editor."""

    source_path: str
    document_bytes: bytes
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    current_path: str = ""
    file_name: str = ""
    source_format: str = ""
    dirty: bool = False
    page_count: int = 0
    status_message: str = ""
    backup_created: bool = False
    backup_path: str = ""
    last_saved_path: str = ""
    last_saved_at: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    allow_hwpx_overwrite: bool = False

    def __post_init__(self) -> None:
        source = Path(self.source_path)
        if not self.current_path:
            self.current_path = str(source)
        if not self.file_name:
            self.file_name = source.name
        if not self.source_format:
            self.source_format = source.suffix.lower().lstrip(".")

    @classmethod
    def from_file(cls, path: str, *, allow_hwpx_overwrite: bool = False) -> "EditorSession":
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"파일이 존재하지 않습니다: {path}")
        if source.suffix.lower() not in SUPPORTED_EDITOR_SUFFIXES:
            raise ValueError("문서 편집기는 .hwp/.hwpx 파일만 열 수 있습니다.")
        return cls(
            source_path=str(source),
            current_path=str(source),
            file_name=source.name,
            source_format=source.suffix.lower().lstrip("."),
            document_bytes=source.read_bytes(),
            allow_hwpx_overwrite=allow_hwpx_overwrite,
        )

    @property
    def display_name(self) -> str:
        return Path(self.current_path or self.source_path).name or self.file_name

    def verify_token(self, token: str) -> bool:
        return secrets.compare_digest(self.token, str(token or ""))

    def update_state(self, payload: dict[str, Any]) -> None:
        if "dirty" in payload:
            self.dirty = bool(payload.get("dirty"))
        if "page_count" in payload:
            try:
                self.page_count = max(0, int(payload.get("page_count") or 0))
            except Exception:
                self.page_count = 0
        if "source_format" in payload:
            value = str(payload.get("source_format") or "").strip().lower()
            if value:
                self.source_format = value
        if "status_message" in payload:
            self.status_message = str(payload.get("status_message") or "")
        self.updated_at = _now_iso()

    def mark_saved(self, path: str, content: bytes) -> None:
        self.current_path = str(Path(path))
        self.last_saved_path = self.current_path
        self.last_saved_at = _now_iso()
        self.file_name = Path(path).name
        self.source_format = Path(path).suffix.lower().lstrip(".") or self.source_format
        self.document_bytes = bytes(content)
        self.dirty = False
        self.updated_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source_path": self.source_path,
            "current_path": self.current_path,
            "file_name": self.file_name,
            "source_format": self.source_format,
            "dirty": self.dirty,
            "page_count": self.page_count,
            "status_message": self.status_message,
            "backup_created": self.backup_created,
            "backup_path": self.backup_path,
            "last_saved_path": self.last_saved_path,
            "last_saved_at": self.last_saved_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
