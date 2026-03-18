from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TypedDict


class TemplateCategory(Enum):
    """템플릿 카테고리"""

    LEAVE = "휴가"
    EXPENSE = "지출"
    MEETING = "회의"
    REPORT = "보고서"
    CONTRACT = "계약"
    LETTER = "공문"
    OTHER = "기타"


@dataclass
class TemplateInfo:
    """템플릿 정보"""

    id: str
    name: str
    description: str
    category: str
    file_path: str
    thumbnail_path: Optional[str] = None
    is_builtin: bool = False
    is_favorite: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    used_count: int = 0
    fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateInfo":
        return cls(**data)


class BuiltinTemplateSpec(TypedDict):
    """내장 템플릿 스펙"""

    id: str
    name: str
    description: str
    category: str
    fields: list[str]
