"""
Merge Split Page
병합/분할 페이지
"""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QFont

from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard


class MergeSplitPage(QWidget):
    """병합/분할 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 제목
        title = QLabel("📎 문서 병합/분할")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("여러 HWP 파일을 병합하거나 페이지별로 분할합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # 탭 버튼
        tab_layout = QHBoxLayout()
        self.merge_btn = QPushButton("📎 파일 병합")
        self.merge_btn.setCheckable(True)
        self.merge_btn.setChecked(True)
        self.merge_btn.setMinimumWidth(150)
        
        self.split_btn = QPushButton("✂️ 페이지 분할")
        self.split_btn.setCheckable(True)
        self.split_btn.setMinimumWidth(150)
        
        tab_layout.addWidget(self.merge_btn)
        tab_layout.addWidget(self.split_btn)
        tab_layout.addStretch()
        layout.addLayout(tab_layout)
        
        # 파일 목록
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)
        
        # 진행률 카드
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)
        
        # 실행 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.execute_btn = QPushButton("실행")
        self.execute_btn.setMinimumSize(150, 45)
        btn_layout.addWidget(self.execute_btn)
        
        layout.addLayout(btn_layout)
