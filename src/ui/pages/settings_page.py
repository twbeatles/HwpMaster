"""
Settings Page
설정 페이지
"""
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class SettingsPage(QWidget):
    """설정 페이지"""
    
    theme_changed = Signal(bool)  # True = Dark, False = Light
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 제목
        title = QLabel("⚙️ 설정")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # 테마 설정
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("다크 모드"))
        
        self.theme_toggle = QPushButton("🌙")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setChecked(True)
        self.theme_toggle.setObjectName("themeToggle")
        self.theme_toggle.clicked.connect(lambda checked: self.theme_changed.emit(checked))
        theme_layout.addWidget(self.theme_toggle)
        theme_layout.addStretch()
        
        layout.addLayout(theme_layout)
        
        # 출력 디렉토리 설정
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("기본 출력 폴더:"))
        
        self.output_label = QLabel(str(Path.home() / "Documents" / "HWP Master"))
        self.output_label.setStyleSheet("color: #888888;")
        output_layout.addWidget(self.output_label, 1)
        
        self.output_btn = QPushButton("변경...")
        self.output_btn.setMinimumWidth(100)
        output_layout.addWidget(self.output_btn)
        
        layout.addLayout(output_layout)
        
        layout.addStretch()
        
        # 버전 정보
        version_label = QLabel("HWP Master v1.0.0")
        version_label.setStyleSheet("color: #666666;")
        layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignCenter)
