"""
Sidebar Button Widget
"""
import os
from typing import Optional

from PySide6.QtWidgets import QPushButton, QWidget
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

class SidebarButton(QPushButton):
    """사이드바 네비게이션 버튼"""
    
    def __init__(
        self, 
        text: str, 
        icon_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))
