"""
Data Inject Page
데이터 주입 페이지
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit

from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader


class DataInjectPage(QWidget):
    """데이터 주입 페이지"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = PageHeader(
            "데이터 자동 입력",
            "Excel/CSV 데이터를 HWP 템플릿 누름틀에 자동으로 주입합니다.",
            "🧩",
        )
        layout.addWidget(header)

        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("템플릿 파일:"))

        self.template_label = QLabel("선택된 파일 없음")
        self.template_label.setStyleSheet("color: #888888;")
        template_layout.addWidget(self.template_label, 1)

        self.template_btn = QPushButton("찾아보기...")
        self.template_btn.setMinimumWidth(100)
        template_layout.addWidget(self.template_btn)

        layout.addLayout(template_layout)

        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("데이터 파일:"))

        self.data_label = QLabel("선택된 파일 없음")
        self.data_label.setStyleSheet("color: #888888;")
        data_layout.addWidget(self.data_label, 1)

        self.data_btn = QPushButton("찾아보기...")
        self.data_btn.setMinimumWidth(100)
        data_layout.addWidget(self.data_btn)

        layout.addLayout(data_layout)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("기본 출력 폴더:"))

        self.output_label = QLabel("")
        self.output_label.setStyleSheet("color: #888888;")
        output_layout.addWidget(self.output_label, 1)

        self.output_btn = QPushButton("변경...")
        self.output_btn.setMinimumWidth(100)
        output_layout.addWidget(self.output_btn)

        layout.addLayout(output_layout)

        filename_field_layout = QHBoxLayout()
        filename_field_layout.addWidget(QLabel("파일명 필드(선택):"))
        self.filename_field_edit = QLineEdit()
        self.filename_field_edit.setPlaceholderText("예: 문서명")
        filename_field_layout.addWidget(self.filename_field_edit, 1)
        layout.addLayout(filename_field_layout)

        filename_template_layout = QHBoxLayout()
        filename_template_layout.addWidget(QLabel("파일명 템플릿(선택):"))
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setPlaceholderText("예: {부서}_{성명}_{index}")
        filename_template_layout.addWidget(self.filename_template_edit, 1)
        layout.addLayout(filename_template_layout)

        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.execute_btn = QPushButton("생성 시작")
        self.execute_btn.setMinimumSize(150, 45)
        btn_layout.addWidget(self.execute_btn)

        layout.addLayout(btn_layout)
