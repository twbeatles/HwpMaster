"""
Home Page
홈 대시보드 페이지
"""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from ..widgets.feature_card import FeatureCard


class HomePage(QWidget):
    """홈 대시보드 페이지"""
    
    card_clicked = Signal(int)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # 환영 메시지
        welcome_label = QLabel("HWP Master에 오신 것을 환영합니다")
        welcome_label.setProperty("class", "title")
        welcome_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        layout.addWidget(welcome_label)
        
        subtitle = QLabel("HWP 업무 자동화를 위한 올인원 도구")
        subtitle.setProperty("class", "subtitle")
        subtitle.setFont(QFont("Segoe UI", 14))
        layout.addWidget(subtitle)
        
        layout.addSpacing(32)
        
        # 기능 카드 그리드
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        card_data = [
            ("🔄 스마트 변환", "HWP → PDF, TXT, HWPX, JPG 일괄 변환"),
            ("📎 병합/분할", "여러 파일 병합 및 페이지별 분할"),
            ("📝 데이터 주입", "Excel 데이터를 HWP 템플릿에 자동 입력"),
            ("🧹 메타정보 정리", "작성자, 메모 등 민감정보 일괄 삭제"),
        ]
        
        for idx, (title, desc) in enumerate(card_data):
            card = FeatureCard(title, desc)
            card.clicked.connect(lambda i=idx: self.card_clicked.emit(i + 1))
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        layout.addLayout(cards_layout)
        
        layout.addStretch()
