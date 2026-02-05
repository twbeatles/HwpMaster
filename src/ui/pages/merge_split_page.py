"""
Merge Split Page
병합/분할 페이지
"""
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox
)
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
        self.merge_btn.clicked.connect(self._on_tab_changed)
        
        self.split_btn = QPushButton("✂️ 페이지 분할")
        self.split_btn.setCheckable(True)
        self.split_btn.setMinimumWidth(150)
        self.split_btn.clicked.connect(self._on_tab_changed)
        
        tab_layout.addWidget(self.merge_btn)
        tab_layout.addWidget(self.split_btn)
        tab_layout.addStretch()
        layout.addLayout(tab_layout)
        
        # 파일 목록
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)
        
        # 분할 옵션 (분할 모드에서만 표시)
        self.split_options = QGroupBox("📋 분할 옵션")
        split_layout = QVBoxLayout(self.split_options)
        
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("페이지 범위:"))
        self.page_range_input = QLineEdit()
        self.page_range_input.setPlaceholderText("예: 1-3, 4-6, 7-10 (콤마로 구분)")
        self.page_range_input.setMinimumWidth(300)
        range_layout.addWidget(self.page_range_input)
        range_layout.addStretch()
        split_layout.addLayout(range_layout)
        
        hint_label = QLabel("💡 각 범위별로 별도의 HWP 파일이 생성됩니다")
        hint_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        split_layout.addWidget(hint_label)
        
        self.split_options.setVisible(False)  # 초기에는 숨김
        layout.addWidget(self.split_options)
        
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
    
    def _on_tab_changed(self) -> None:
        """탭 변경 시 UI 업데이트"""
        sender = self.sender()
        if sender == self.merge_btn:
            self.merge_btn.setChecked(True)
            self.split_btn.setChecked(False)
            self.split_options.setVisible(False)
        else:
            self.merge_btn.setChecked(False)
            self.split_btn.setChecked(True)
            self.split_options.setVisible(True)
    
    def get_page_ranges(self) -> list[str]:
        """페이지 범위 문자열 리스트 반환"""
        text = self.page_range_input.text().strip()
        if not text:
            return []
        return [r.strip() for r in text.split(",") if r.strip()]

