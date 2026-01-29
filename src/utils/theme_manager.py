"""
Theme Manager Module
테마 커스터마이징 관리

Author: HWP Master
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class ThemeColors:
    """테마 색상"""
    primary: str = "#8957e5"
    secondary: str = "#238636"
    background: str = "#0d1117"
    surface: str = "#161b22"
    border: str = "#30363d"
    text_primary: str = "#e6edf3"
    text_secondary: str = "#8b949e"
    success: str = "#3fb950"
    error: str = "#f85149"
    warning: str = "#d29922"


# 프리셋 테마
THEME_PRESETS: dict[str, ThemeColors] = {
    "Dark (기본)": ThemeColors(),
    "Dark Purple": ThemeColors(
        primary="#a855f7",
        background="#0f0a1a",
        surface="#1a1025"
    ),
    "Dark Blue": ThemeColors(
        primary="#3b82f6",
        background="#0a0f1a",
        surface="#101825"
    ),
    "Dark Green": ThemeColors(
        primary="#22c55e",
        secondary="#8957e5",
        background="#0a1a0f",
        surface="#102518"
    ),
    "Light": ThemeColors(
        primary="#7c3aed",
        background="#ffffff",
        surface="#f8fafc",
        border="#e2e8f0",
        text_primary="#1e293b",
        text_secondary="#64748b"
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
