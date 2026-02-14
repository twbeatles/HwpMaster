"""
QSS template rendering and stylesheet building.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Mapping

from .theme_manager import get_theme_manager


_TOKEN_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def _base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # src/utils/qss_renderer.py -> project root
    return Path(__file__).resolve().parents[2]


def load_qss_template_text() -> str:
    base = _base_path()
    template_path = base / "assets" / "styles" / "style.template.qss"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    fallback = base / "assets" / "styles" / "style.qss"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")

    raise FileNotFoundError("스타일시트 파일을 찾을 수 없습니다 (style.template.qss/style.qss).")


def render_qss(template_text: str, tokens: Mapping[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in tokens:
            raise KeyError(f"QSS 토큰이 없습니다: {key}")
        return tokens[key]

    rendered = _TOKEN_RE.sub(repl, template_text)
    leftover = _TOKEN_RE.search(rendered)
    if leftover:
        raise ValueError(f"QSS 렌더링 후 미치환 토큰이 남아있습니다: {leftover.group(0)}")
    return rendered


def build_stylesheet(theme_preset: str) -> str:
    theme = get_theme_manager()
    theme.set_theme(theme_preset)
    tokens = theme.get_colors().to_tokens()
    template = load_qss_template_text()
    return render_qss(template, tokens)
