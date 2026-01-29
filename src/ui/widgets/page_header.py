"""
Page Header Widget
페이지 헤더 컴포넌트

Author: HWP Master
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class PageHeader(QWidget):
    """통일된 페이지 헤더"""
    
    action_clicked = Signal(str)
    
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        icon: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeader")
        
        self._actions: list[QPushButton] = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 24)
        layout.setSpacing(8)
        
        # 상단 (타이틀 + 액션 버튼)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        
        # 아이콘 + 타이틀
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 32px; background: transparent;")
            title_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setProperty("class", "title")
        title_label.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title_label.setStyleSheet("background: transparent;")
        title_layout.addWidget(title_label)
        
        top_layout.addLayout(title_layout)
        top_layout.addStretch()
        
        # 액션 버튼 영역
        self._action_layout = QHBoxLayout()
        self._action_layout.setSpacing(8)
        top_layout.addLayout(self._action_layout)
        
        layout.addLayout(top_layout)
        
        # 부제목
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("class", "subtitle")
            subtitle_label.setStyleSheet("""
                color: #8b949e;
                font-size: 15px;
                background: transparent;
            """)
            layout.addWidget(subtitle_label)
        
        # 하단 구분선
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #21262d;")
        layout.addWidget(line)
    
    def add_action(
        self,
        text: str,
        action_id: str,
        icon: str = "",
        primary: bool = False
    ) -> QPushButton:
        """액션 버튼 추가"""
        btn_text = f"{icon} {text}".strip() if icon else text
        btn = QPushButton(btn_text)
        
        if primary:
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #8957e5, stop:1 #6e40c9);
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    color: white;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #a371f7, stop:1 #8957e5);
                }
            """)
        else:
            btn.setProperty("class", "secondary")
        
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.action_clicked.emit(action_id))
        
        self._action_layout.addWidget(btn)
        self._actions.append(btn)
        
        return btn
    
    def set_action_enabled(self, action_id: str, enabled: bool) -> None:
        """액션 버튼 활성화/비활성화"""
        for btn in self._actions:
            if btn.text() == action_id:
                btn.setEnabled(enabled)
                break


class SectionHeader(QWidget):
    """섹션 헤더 (작은 제목)"""
    
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 12)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e6edf3; background: transparent;")
        layout.addWidget(title_label)
        
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("color: #8b949e; font-size: 13px; background: transparent;")
            layout.addWidget(subtitle_label)


class StatCard(QWidget):
    """통계 카드"""
    
    def __init__(
        self,
        label: str,
        value: str,
        icon: str = "",
        color: str = "#8957e5",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # 아이콘
        if icon:
            icon_container = QWidget()
            icon_container.setFixedSize(48, 48)
            icon_container.setStyleSheet(f"""
                background-color: {color}20;
                border-radius: 12px;
            """)
            icon_layout = QVBoxLayout(icon_container)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            
            icon_label = QLabel(icon)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(f"font-size: 22px; background: transparent;")
            icon_layout.addWidget(icon_label)
            
            layout.addWidget(icon_container)
        
        # 텍스트
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color}; background: transparent;")
        text_layout.addWidget(value_label)
        
        label_label = QLabel(label)
        label_label.setStyleSheet("color: #8b949e; font-size: 13px; background: transparent;")
        text_layout.addWidget(label_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
    
    def set_value(self, value: str) -> None:
        """값 업데이트"""
        for child in self.findChildren(QLabel):
            if child.font().pointSize() >= 20:
                child.setText(value)
                break
