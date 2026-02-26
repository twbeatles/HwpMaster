"""
Feature Card Widget
기능 카드 위젯

Author: HWP Master
"""
import os
from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont


class FeatureCard(QFrame):
    """기능 카드 위젯"""
    
    clicked = Signal()
    
    def __init__(
        self,
        title: str,
        description: str,
        icon_emoji: str = "",
        icon_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        
        # 아이콘 + 제목 (수평 레이아웃)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # 이모지 아이콘 (우선) 또는 파일 아이콘
        if icon_emoji:
            emoji_label = QLabel(icon_emoji)
            emoji_label.setStyleSheet("""
                font-size: 28px;
                background: transparent;
            """)
            emoji_label.setFixedSize(36, 36)
            emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(emoji_label)
        elif icon_path and os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon_path).pixmap(28, 28))
            icon_label.setStyleSheet("background: transparent;")
            header_layout.addWidget(icon_label)
        
        # 제목
        title_label = QLabel(title)
        title_label.setProperty("class", "card-title")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("background: transparent;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # 설명
        desc_label = QLabel(description)
        desc_label.setProperty("class", "card-description")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("background: transparent;")
        layout.addWidget(desc_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
