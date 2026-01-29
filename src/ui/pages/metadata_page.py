"""
Metadata Page
메타데이터 정리 페이지
"""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QFont

from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard


class MetadataPage(QWidget):
    """메타데이터 정리 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 제목
        title = QLabel("🧹 메타정보 정리")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("문서의 민감한 메타정보를 일괄 삭제합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # 파일 목록
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)
        
        # 옵션 체크박스들 (간단한 라벨로 대체)
        options_label = QLabel("✓ 작성자 정보 제거  ✓ 메모 삭제  ✓ 변경 추적 제거  ✓ 배포용 설정")
        options_label.setStyleSheet("color: #7952b3;")
        layout.addWidget(options_label)
        
        # 진행률 카드
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)
        
        # 실행 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.execute_btn = QPushButton("정리 시작")
        self.execute_btn.setMinimumSize(150, 45)
        btn_layout.addWidget(self.execute_btn)
        
        layout.addLayout(btn_layout)
