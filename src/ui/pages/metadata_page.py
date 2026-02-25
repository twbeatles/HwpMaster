"""
Metadata Page
메타정보/보안 정리 페이지
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QLineEdit,
)

from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader


class MetadataPage(QWidget):
    """메타정보/보안 정리 페이지"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = PageHeader(
            "메타정보 정리",
            "문서의 메타정보를 정리하고 배포/보안 옵션을 적용합니다.",
            "🧹",
        )
        layout.addWidget(header)

        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("기본 출력 폴더:"))
        self.output_label = QLabel("")
        self.output_label.setStyleSheet("color: #8b949e;")
        output_layout.addWidget(self.output_label, 1)
        self.output_btn = QPushButton("변경...")
        self.output_btn.setProperty("class", "secondary")
        output_layout.addWidget(self.output_btn)
        layout.addLayout(output_layout)

        self.remove_author_check = QCheckBox("작성자/회사 정보 제거")
        self.remove_author_check.setChecked(True)
        layout.addWidget(self.remove_author_check)

        self.remove_comments_check = QCheckBox("메모(주석) 제거")
        self.remove_comments_check.setChecked(True)
        layout.addWidget(self.remove_comments_check)

        self.remove_tracking_check = QCheckBox("변경 추적 이력 정리")
        self.remove_tracking_check.setChecked(True)
        layout.addWidget(self.remove_tracking_check)

        self.set_distribution_check = QCheckBox("배포용 문서 설정")
        self.set_distribution_check.setChecked(True)
        layout.addWidget(self.set_distribution_check)

        self.scan_pii_check = QCheckBox("개인정보 패턴 스캔(주민번호/연락처/이메일)")
        self.scan_pii_check.setChecked(False)
        layout.addWidget(self.scan_pii_check)

        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("문서 암호(선택):"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("비워두면 암호 미설정")
        password_layout.addWidget(self.password_edit, 1)
        layout.addLayout(password_layout)

        self.strict_password_check = QCheckBox("암호 설정 실패 시 파일 처리 실패")
        self.strict_password_check.setChecked(False)
        layout.addWidget(self.strict_password_check)

        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.execute_btn = QPushButton("정리 시작")
        self.execute_btn.setMinimumSize(150, 45)
        btn_layout.addWidget(self.execute_btn)

        layout.addLayout(btn_layout)
