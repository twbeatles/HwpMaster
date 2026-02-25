"""
Capability mapper for pyhwpx coverage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .hwp_handler import CapabilitySnapshot, HwpHandler


@dataclass
class CoverageResult:
    """Coverage report for pyhwpx usage in this repository."""

    total_public_methods: int
    used_public_methods: int
    usage_ratio_percent: float
    used_methods: list[str] = field(default_factory=list)
    used_actions: list[str] = field(default_factory=list)
    category_totals: dict[str, int] = field(default_factory=dict)
    category_used: dict[str, int] = field(default_factory=dict)


class CapabilityMapper:
    """Calculate pyhwpx capability coverage against repository usage."""

    _METHOD_PATTERN = re.compile(r"\b(?:hwp|self\._hwp)\.([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    _RUN_ACTION_PATTERN = re.compile(r"\.HAction\.Run\(\"([^\"]+)\"\)")
    _EXEC_ACTION_PATTERN = re.compile(r"\.HAction\.(?:Execute|GetDefault)\(\"([^\"]+)\"")

    def __init__(self, repo_root: str | Path | None = None) -> None:
        if repo_root is None:
            self._repo_root = Path(__file__).resolve().parents[2]
        else:
            self._repo_root = Path(repo_root).resolve()

    @staticmethod
    def _categorize(name: str) -> str:
        lowered = name.lower()
        if lowered.startswith(("file", "open", "save", "close", "quit")):
            return "file_io"
        if "field" in lowered or "metatag" in lowered or lowered.startswith("form"):
            return "field_form"
        if "find" in lowered or "replace" in lowered:
            return "find_replace"
        if "charshape" in lowered or "parashape" in lowered or "style" in lowered:
            return "style_format"
        if "table" in lowered or "cell" in lowered:
            return "table"
        if "shape" in lowered or "draw" in lowered or "picture" in lowered or "image" in lowered:
            return "shape_graphic"
        if "private" in lowered or "encrypt" in lowered or "distribution" in lowered or "trackchange" in lowered:
            return "security_privacy"
        if "macro" in lowered or "script" in lowered:
            return "automation_macro"
        if lowered.startswith(("move", "goto", "select")):
            return "navigation_selection"
        return "other"

    def _scan_repository_usage(self) -> tuple[set[str], set[str]]:
        used_methods: set[str] = set()
        used_actions: set[str] = set()

        src_root = self._repo_root / "src"
        if not src_root.exists():
            return used_methods, used_actions

        for py_file in src_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            used_methods.update(self._METHOD_PATTERN.findall(text))
            used_actions.update(self._RUN_ACTION_PATTERN.findall(text))
            used_actions.update(self._EXEC_ACTION_PATTERN.findall(text))

        return used_methods, used_actions

    def build_coverage(self, snapshot: CapabilitySnapshot | None = None) -> CoverageResult:
        cap = snapshot or HwpHandler.introspect_capabilities()
        used_methods_raw, used_actions = self._scan_repository_usage()
        cap_methods = set(cap.methods)
        used_methods = sorted(m for m in used_methods_raw if m in cap_methods)

        totals: dict[str, int] = {}
        used_by_cat: dict[str, int] = {}
        for name in cap.methods:
            cat = self._categorize(name)
            totals[cat] = totals.get(cat, 0) + 1
        for name in used_methods:
            cat = self._categorize(name)
            used_by_cat[cat] = used_by_cat.get(cat, 0) + 1

        total_public = max(len(cap.methods), 1)
        ratio = (len(used_methods) / total_public) * 100.0
        return CoverageResult(
            total_public_methods=len(cap.methods),
            used_public_methods=len(used_methods),
            usage_ratio_percent=ratio,
            used_methods=used_methods,
            used_actions=sorted(used_actions),
            category_totals=totals,
            category_used=used_by_cat,
        )

    def as_dict(self, snapshot: CapabilitySnapshot | None = None) -> dict[str, Any]:
        cov = self.build_coverage(snapshot)
        return {
            "total_public_methods": cov.total_public_methods,
            "used_public_methods": cov.used_public_methods,
            "usage_ratio_percent": cov.usage_ratio_percent,
            "used_methods": cov.used_methods,
            "used_actions": cov.used_actions,
            "category_totals": cov.category_totals,
            "category_used": cov.category_used,
        }

