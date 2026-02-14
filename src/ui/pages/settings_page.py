"""
Settings Page
설정 페이지
"""
import subprocess
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QApplication, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

from ...utils.theme_manager import ThemeManager
from ...utils.version import APP_NAME, APP_VERSION


class SettingsPage(QWidget):
    """설정 페이지"""
    
    theme_preset_changed = Signal(str)
    hyperlink_external_requests_enabled_changed = Signal(bool)
    hyperlink_timeout_sec_changed = Signal(int)
    hyperlink_domain_allowlist_changed = Signal(str)
    
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
        theme_layout.addWidget(QLabel("테마 프리셋:"))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemeManager.get_presets())
        self.theme_combo.currentTextChanged.connect(self.theme_preset_changed.emit)
        theme_layout.addWidget(self.theme_combo)
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

        # 하이퍼링크 검사 (네트워크/프라이버시)
        hyperlink_layout = QVBoxLayout()
        hyperlink_header = QLabel("하이퍼링크 검사")
        hyperlink_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        hyperlink_layout.addWidget(hyperlink_header)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("외부 URL 접속:"))
        self.hyperlink_external_checkbox = QCheckBox("외부 사이트에 실제로 접속하여 검사 (네트워크 요청 발생)")
        self.hyperlink_external_checkbox.toggled.connect(self.hyperlink_external_requests_enabled_changed.emit)
        row1.addWidget(self.hyperlink_external_checkbox, 1)
        hyperlink_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("타임아웃(초):"))
        self.hyperlink_timeout_spin = QSpinBox()
        self.hyperlink_timeout_spin.setRange(1, 60)
        self.hyperlink_timeout_spin.valueChanged.connect(self.hyperlink_timeout_sec_changed.emit)
        row2.addWidget(self.hyperlink_timeout_spin)
        row2.addStretch()
        hyperlink_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("도메인 allowlist:"))
        self.hyperlink_allowlist_edit = QLineEdit()
        self.hyperlink_allowlist_edit.setPlaceholderText("example.com, *.corp.local")
        self.hyperlink_allowlist_edit.textChanged.connect(self.hyperlink_domain_allowlist_changed.emit)
        row3.addWidget(self.hyperlink_allowlist_edit, 1)
        hyperlink_layout.addLayout(row3)

        hint = QLabel("allowlist가 비어있으면 모든 도메인에 대해 검사합니다. allowlist가 있으면 매칭되는 도메인만 접속합니다.")
        hint.setStyleSheet("color: #666666;")
        hint.setWordWrap(True)
        hyperlink_layout.addWidget(hint)

        layout.addLayout(hyperlink_layout)

        # 프로세스 정리 (옵션)
        cleanup_layout = QHBoxLayout()
        cleanup_layout.addWidget(QLabel("한글 프로세스:"))

        self.cleanup_btn = QPushButton("정리...")
        self.cleanup_btn.setProperty("class", "secondary")
        self.cleanup_btn.clicked.connect(self._cleanup_hwp_process)
        cleanup_layout.addWidget(self.cleanup_btn)
        cleanup_layout.addStretch()

        layout.addLayout(cleanup_layout)
        
        layout.addStretch()
        
        # 버전 정보
        version = QApplication.applicationVersion() or APP_VERSION
        version_label = QLabel(f"{APP_NAME} v{version}")
        version_label.setStyleSheet("color: #666666;")
        layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def _cleanup_hwp_process(self) -> None:
        reply = QMessageBox.question(
            self,
            "한글 프로세스 정리",
            "실행 중인 한글(hwp.exe) 프로세스를 강제 종료합니다.\n"
            "열려있는 문서가 있다면 저장되지 않은 내용이 사라질 수 있습니다.\n\n"
            "정리하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # /T: child process 포함, /F: 강제 종료
            proc = subprocess.run(
                ["taskkill", "/IM", "hwp.exe", "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                QMessageBox.information(self, "완료", "한글(hwp.exe) 프로세스를 종료했습니다.")
            else:
                # 이미 종료되어 있거나 권한 문제일 수 있음
                msg = (proc.stdout or "") + (proc.stderr or "")
                msg = msg.strip()
                QMessageBox.information(
                    self,
                    "안내",
                    "종료할 한글(hwp.exe) 프로세스가 없거나 종료에 실패했습니다."
                    + (f"\n\n{msg}" if msg else ""),
                )
        except Exception as e:
            QMessageBox.warning(self, "오류", f"프로세스 정리 중 오류가 발생했습니다:\n{e}")
