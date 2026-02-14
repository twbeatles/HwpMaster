"""
Theme Manager Module
테마 커스터마이징 관리

Author: HWP Master
"""

from typing import Optional
from dataclasses import dataclass
import re


@dataclass
class ThemeColors:
    """테마 색상"""
    primary: str = "#8957e5"
    primary2: str = "#6e40c9"
    primary_light: str = "#a371f7"
    primary_dark: str = "#553098"
    secondary: str = "#238636"
    background: str = "#0d1117"
    surface: str = "#161b22"
    surface_alt: str = "#1c2128"
    surface_muted: str = "#21262d"
    border: str = "#30363d"
    text_primary: str = "#e6edf3"
    text_secondary: str = "#8b949e"
    text_muted: str = "#484f58"
    accent: str = "#58a6ff"
    success: str = "#3fb950"
    success_mid: str = "#2ea043"
    success_dark: str = "#238636"
    error: str = "#f85149"
    error_dark: str = "#da3633"
    warning: str = "#d29922"
    white: str = "#ffffff"

    def to_tokens(self) -> dict[str, str]:
        """
        QSS 템플릿 토큰 dict로 변환.

        - hex 색상 토큰: 그대로 사용 (#RRGGBB)
        - rgba 토큰: 템플릿에서 rgba(...) 형태로 사용
        """

        def hex_to_rgb(h: str) -> tuple[int, int, int]:
            m = re.fullmatch(r"#([0-9a-fA-F]{6})", h)
            if not m:
                raise ValueError(f"잘못된 HEX 색상: {h}")
            v = m.group(1)
            return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)

        def rgba(hex_color: str, alpha: float) -> str:
            r, g, b = hex_to_rgb(hex_color)
            return f"rgba({r}, {g}, {b}, {alpha})"

        tokens: dict[str, str] = {
            "primary": self.primary,
            "primary2": self.primary2,
            "primary_light": self.primary_light,
            "primary_dark": self.primary_dark,
            "secondary": self.secondary,
            "background": self.background,
            "surface": self.surface,
            "surface_alt": self.surface_alt,
            "surface_muted": self.surface_muted,
            "border": self.border,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "text_muted": self.text_muted,
            "accent": self.accent,
            "success": self.success,
            "success_mid": self.success_mid,
            "success_dark": self.success_dark,
            "error": self.error,
            "error_dark": self.error_dark,
            "warning": self.warning,
            "white": self.white,
            # Common rgba variants used by style.template.qss
            "primary_rgba_05": rgba(self.primary, 0.05),
            "primary_rgba_10": rgba(self.primary, 0.1),
            "primary_rgba_20": rgba(self.primary, 0.2),
            "primary_rgba_30": rgba(self.primary, 0.3),
            "primary_rgba_40": rgba(self.primary, 0.4),
            "accent_rgba_10": rgba(self.accent, 0.1),
            "accent_rgba_15": rgba(self.accent, 0.15),
            "accent_rgba_20": rgba(self.accent, 0.2),
            "text_secondary_rgba_10": rgba(self.text_secondary, 0.1),
            "text_secondary_rgba_15": rgba(self.text_secondary, 0.15),
            "surface_rgba_80": rgba(self.surface, 0.8),
            "border_rgba_60": rgba(self.border, 0.6),
            "success_rgba_15": rgba(self.success, 0.15),
            "success_rgba_20": rgba(self.success, 0.2),
            "error_rgba_15": rgba(self.error, 0.15),
            "error_rgba_20": rgba(self.error, 0.2),
            "warning_rgba_15": rgba(self.warning, 0.15),
            "warning_rgba_20": rgba(self.warning, 0.2),
        }
        return tokens


# 프리셋 테마
THEME_PRESETS: dict[str, ThemeColors] = {
    "Dark (기본)": ThemeColors(),
    "Dark Purple": ThemeColors(
        primary="#a855f7",
        primary2="#7c3aed",
        primary_light="#c084fc",
        primary_dark="#5b21b6",
        background="#0f0a1a",
        surface="#1a1025",
        surface_alt="#221333",
        surface_muted="#2a1a3f",
        border="#3a2756",
        accent="#60a5fa",
    ),
    "Dark Blue": ThemeColors(
        primary="#3b82f6",
        primary2="#2563eb",
        primary_light="#60a5fa",
        primary_dark="#1d4ed8",
        background="#0a0f1a",
        surface="#101825",
        surface_alt="#141f33",
        surface_muted="#19243a",
        border="#26344d",
        accent="#58a6ff",
    ),
    "Dark Green": ThemeColors(
        primary="#22c55e",
        primary2="#16a34a",
        primary_light="#4ade80",
        primary_dark="#15803d",
        secondary="#8957e5",
        background="#0a1a0f",
        surface="#102518",
        surface_alt="#142f20",
        surface_muted="#193624",
        border="#244a32",
        accent="#58a6ff",
    ),
    "Light": ThemeColors(
        primary="#7c3aed",
        primary2="#6d28d9",
        primary_light="#8b5cf6",
        primary_dark="#5b21b6",
        background="#ffffff",
        surface="#f8fafc",
        surface_alt="#f1f5f9",
        surface_muted="#e2e8f0",
        border="#e2e8f0",
        text_primary="#1e293b",
        text_secondary="#64748b",
        text_muted="#94a3b8",
        accent="#2563eb",
        success="#16a34a",
        success_mid="#22c55e",
        success_dark="#15803d",
        error="#dc2626",
        error_dark="#b91c1c",
        warning="#d97706",
        white="#ffffff",
    ),
}


class ThemeManager:
    """테마 관리자"""
    
    def __init__(self) -> None:
        self._current_theme = "Dark (기본)"
        self._colors = THEME_PRESETS[self._current_theme]
    
    @staticmethod
    def get_presets() -> list[str]:
        """프리셋 목록 반환"""
        return list(THEME_PRESETS.keys())
    
    def get_current_theme(self) -> str:
        """현재 테마 반환"""
        return self._current_theme
    
    def set_theme(self, theme_name: str) -> bool:
        """테마 설정"""
        if theme_name in THEME_PRESETS:
            self._current_theme = theme_name
            self._colors = THEME_PRESETS[theme_name]
            return True
        return False
    
    def get_colors(self) -> ThemeColors:
        """현재 테마 색상 반환"""
        return self._colors
    
    def generate_qss(self) -> str:
        """QSS 스타일시트 생성"""
        c = self._colors
        return f"""
/* 메인 윈도우 */
QMainWindow, QWidget {{
    background-color: {c.background};
    color: {c.text_primary};
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
}}

/* 사이드바 */
#sidebar {{
    background-color: {c.surface};
    border-right: 1px solid {c.border};
}}

/* 버튼 */
QPushButton {{
    background-color: {c.primary};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {c.primary}dd;
}}
QPushButton:pressed {{
    background-color: {c.primary}bb;
}}
QPushButton[class="secondary"] {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    color: {c.text_primary};
}}

/* 입력 필드 */
QLineEdit, QTextEdit, QComboBox, QSpinBox {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 6px;
    padding: 8px 12px;
    color: {c.text_primary};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {c.primary};
}}

/* 테이블 */
QTableWidget {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 8px;
    gridline-color: {c.border};
}}
QTableWidget::item {{
    padding: 8px;
}}
QHeaderView::section {{
    background-color: {c.background};
    border: none;
    border-bottom: 1px solid {c.border};
    padding: 8px;
    font-weight: bold;
}}

/* 리스트 */
QListWidget {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 8px;
}}
QListWidget::item {{
    padding: 10px;
    border-bottom: 1px solid {c.border};
}}
QListWidget::item:selected {{
    background-color: {c.primary}33;
}}

/* 그룹박스 */
QGroupBox {{
    border: 1px solid {c.border};
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    color: {c.text_secondary};
    padding: 0 8px;
}}

/* 프로그레스바 */
QProgressBar {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {c.primary};
    border-radius: 5px;
}}

/* 슬라이더 */
QSlider::groove:horizontal {{
    background: {c.border};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {c.primary};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

/* 스크롤바 */
QScrollBar:vertical {{
    background: {c.background};
    width: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background: {c.border};
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c.primary}88;
}}
"""


# 싱글톤
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """테마 관리자 인스턴스 반환"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
