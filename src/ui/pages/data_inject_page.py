"""
Data Inject Page
데이터 주입 페이지
"""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QFont

from ..widgets.progress_card import ProgressCard


class DataInjectPage(QWidget):
    """데이터 주입 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 제목
        title = QLabel("📝 데이터 자동 입력")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("Excel 데이터를 HWP 템플릿에 자동으로 입력합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # 템플릿 선택
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("템플릿 파일:"))
        
        self.template_label = QLabel("선택된 파일 없음")
        self.template_label.setStyleSheet("color: #888888;")
        template_layout.addWidget(self.template_label, 1)
        
        self.template_btn = QPushButton("찾아보기...")
        self.template_btn.setMinimumWidth(100)
        template_layout.addWidget(self.template_btn)
        
        layout.addLayout(template_layout)
        
        # 데이터 파일 선택
        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("데이터 파일:"))
        
        self.data_label = QLabel("선택된 파일 없음")
        self.data_label.setStyleSheet("color: #888888;")
        data_layout.addWidget(self.data_label, 1)
        
        self.data_btn = QPushButton("찾아보기...")
        self.data_btn.setMinimumWidth(100)
        data_layout.addWidget(self.data_btn)
        
        layout.addLayout(data_layout)
        
        # 진행률 카드
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)
        
        layout.addStretch()
        
        # 실행 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.execute_btn = QPushButton("생성 시작")
        self.execute_btn.setMinimumSize(150, 45)
        btn_layout.addWidget(self.execute_btn)
        
        layout.addLayout(btn_layout)
