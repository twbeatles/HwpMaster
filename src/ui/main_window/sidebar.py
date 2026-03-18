from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..widgets.sidebar_button import SidebarButton
from ...utils.version import APP_VERSION


class Sidebar(QFrame):
    """사이드바 네비게이션"""

    page_changed = Signal(int)

    NAV_SECTIONS = [
        ("기본", [("🏠", "홈"), ("🔄", "변환"), ("🔗", "병합/분할"), ("🧩", "데이터 주입"), ("🧹", "메타정보 정리")]),
        ("고급", [("📁", "템플릿 스토어"), ("🎬", "매크로"), ("🧪", "정규식 치환")]),
        ("분석", [("🕵", "서식 교정"), ("📊", "표 교정"), ("📄", "문서 비교"), ("📚", "스마트 목차")]),
        ("생산성", [("💧", "워터마크"), ("📑", "헤더/푸터"), ("🔖", "북마크"), ("🔍", "링크 검사"), ("🖼", "이미지 추출"), ("🧰", "액션 콘솔")]),
        ("", [("⚙", "설정")]),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(280)

        self._is_collapsed = False
        self._buttons: list[SidebarButton] = []
        self._nav_items: list[tuple[str, str]] = []
        self._section_labels: list[QLabel] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 24, 16, 20)
        header_layout.setSpacing(8)

        logo_container = QWidget()
        logo_inner = QHBoxLayout(logo_container)
        logo_inner.setContentsMargins(8, 0, 8, 0)
        logo_inner.setSpacing(14)

        logo_icon = QLabel("📄")
        logo_icon.setStyleSheet("font-size: 30px; background: transparent;")
        logo_inner.addWidget(logo_icon)

        title_container = QWidget()
        title_inner = QVBoxLayout(title_container)
        title_inner.setContentsMargins(0, 0, 0, 0)
        title_inner.setSpacing(2)

        self._title_label = QLabel("HWP Master")
        self._title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #ffffff; background: transparent;")
        title_inner.addWidget(self._title_label)

        version = ""
        try:
            app = QApplication.instance()
            if isinstance(app, QApplication):
                version = app.applicationVersion()
        except Exception:
            version = ""
        self._version_label = QLabel(f"v{version}" if version else f"v{APP_VERSION}")
        self._version_label.setStyleSheet("color: #8957e5; font-size: 11px; background: transparent;")
        title_inner.addWidget(self._version_label)

        logo_inner.addWidget(title_container)
        logo_inner.addStretch()
        header_layout.addWidget(logo_container)
        header_layout.addSpacing(20)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #30363d;")
        header_layout.addWidget(line)

        main_layout.addWidget(header_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 0px; background: transparent; }
            """
        )

        scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(16, 12, 16, 12)
        self._scroll_layout.setSpacing(4)

        btn_index = 0
        for section_name, items in self.NAV_SECTIONS:
            if section_name:
                section_label = QLabel(section_name)
                section_label.setStyleSheet(
                    """
                    color: #484f58;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    padding: 12px 10px 6px 10px;
                    background: transparent;
                    """
                )
                self._section_labels.append(section_label)
                self._scroll_layout.addWidget(section_label)

            for icon, text in items:
                self._nav_items.append((icon, text))
                btn = SidebarButton(f"  {icon}  {text}")
                btn.clicked.connect(lambda checked, i=btn_index: self._on_button_clicked(i))
                self._buttons.append(btn)
                self._scroll_layout.addWidget(btn)
                btn_index += 1

        if self._buttons:
            self._buttons[0].setChecked(True)

        self._scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(12, 10, 12, 16)

        self._toggle_btn = QPushButton("◀  메뉴 접기")
        self._toggle_btn.setMinimumHeight(32)
        self._toggle_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #8b949e;
                font-size: 12px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background: rgba(139, 148, 158, 0.1);
                color: #e6edf3;
            }
            """
        )
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        footer_layout.addWidget(self._toggle_btn)

        main_layout.addWidget(footer_widget)

    def _on_button_clicked(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

    @property
    def is_collapsed(self) -> bool:
        return self._is_collapsed

    def _toggle_collapse(self) -> None:
        self.set_collapsed(not self._is_collapsed, animate=True)

    def set_collapsed(self, collapsed: bool, *, animate: bool = False) -> None:
        if self._is_collapsed == bool(collapsed):
            return
        self._is_collapsed = bool(collapsed)
        target_width = 70 if self._is_collapsed else 280

        if animate:
            animation = QPropertyAnimation(self, b"minimumWidth")
            animation.setDuration(200)
            animation.setEndValue(target_width)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)

            animation2 = QPropertyAnimation(self, b"maximumWidth")
            animation2.setDuration(200)
            animation2.setEndValue(target_width)
            animation2.setEasingCurve(QEasingCurve.Type.OutCubic)

            group = QParallelAnimationGroup(self)
            group.addAnimation(animation)
            group.addAnimation(animation2)
            group.start()
        else:
            self.setMinimumWidth(target_width)
            self.setMaximumWidth(target_width)

        if self._is_collapsed:
            self._toggle_btn.setText("▶")
            self._toggle_btn.setStyleSheet(self._toggle_btn.styleSheet() + "text-align: center; padding-left: 0px;")
        else:
            self._toggle_btn.setText("◀  메뉴 접기")
            self._toggle_btn.setStyleSheet(
                self._toggle_btn.styleSheet().replace(
                    "text-align: center; padding-left: 0px;",
                    "text-align: left; padding-left: 10px;",
                )
            )

        self._title_label.setVisible(not self._is_collapsed)
        self._version_label.setVisible(not self._is_collapsed)

        for label in self._section_labels:
            label.setVisible(not self._is_collapsed)

        for btn, (icon, text) in zip(self._buttons, self._nav_items):
            if self._is_collapsed:
                btn.setText(f"  {icon}")
                btn.setToolTip(text)
            else:
                btn.setText(f"  {icon}  {text}")
                btn.setToolTip("")
