"""
Convert Page
변환 페이지
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
)
from PySide6.QtGui import QFont

from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard


class ConvertPage(QWidget):
    """변환 페이지"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 제목
        title = QLabel("🔄 스마트 일괄 변환")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("HWP 파일을 다양한 포맷으로 일괄 변환합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # 파일 목록 위젯
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)

        # 출력 폴더
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("기본 출력 폴더:"))
        self.output_label = QLabel("")
        self.output_label.setStyleSheet("color: #8b949e;")
        output_layout.addWidget(self.output_label, 1)
        self.output_btn = QPushButton("변경...")
        self.output_btn.setProperty("class", "secondary")
        output_layout.addWidget(self.output_btn)
        layout.addLayout(output_layout)

        # 출력 포맷 선택 (단일 선택)
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("출력 포맷:"))

        self._format_group = QButtonGroup(self)
        self._format_group.setExclusive(True)

        self.format_buttons: list[QPushButton] = []
        for fmt in ["PDF", "TXT", "HWPX", "JPG"]:
            btn = QPushButton(fmt)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            if fmt == "PDF":
                btn.setChecked(True)
            self._format_group.addButton(btn)
            self.format_buttons.append(btn)
            format_layout.addWidget(btn)

        format_layout.addStretch()
        layout.addLayout(format_layout)

        # 진행률 카드
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.convert_btn = QPushButton("변환 시작")
        self.convert_btn.setMinimumSize(150, 45)
        btn_layout.addWidget(self.convert_btn)

        layout.addLayout(btn_layout)

