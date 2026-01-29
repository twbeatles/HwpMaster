"""
Feature Card Widget
"""
import os
from typing import Optional

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

class FeatureCard(QFrame):
    """기능 카드 위젯"""
    
    clicked = Signal()
    
    def __init__(
        self,
        title: str,
        description: str,
        icon_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(200, 150)
        self.setMaximumSize(300, 200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 아이콘 (선택적)
        if icon_path and os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon_path).pixmap(32, 32))
            layout.addWidget(icon_label)
        
        # 제목
        title_label = QLabel(title)
        title_label.setProperty("class", "card-title")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 설명
        desc_label = QLabel(description)
        desc_label.setProperty("class", "card-description")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
