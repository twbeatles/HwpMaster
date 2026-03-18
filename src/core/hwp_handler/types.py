from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConvertFormat(Enum):
    """변환 형식 열거형."""

    PDF = "pdf"
    TXT = "txt"
    HWPX = "hwpx"
    JPG = "jpg"
    HTML = "html"


@dataclass
class ConversionResult:
    """변환 결과 데이터 클래스."""

    success: bool
    source_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class OperationResult:
    """Generic operation result for action APIs."""

    success: bool
    warnings: list[str] = field(default_factory=list)
    changed_count: int = 0
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class CapabilitySnapshot:
    """pyhwpx capability snapshot."""

    pyhwpx_version: str
    method_count: int
    methods: list[str]
    action_count: int
    actions: list[str]
    categories: dict[str, int] = field(default_factory=dict)
    unsupported_categories: list[str] = field(default_factory=list)
