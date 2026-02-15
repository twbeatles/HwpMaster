"""
Settings Page
설정 페이지
"""
import subprocess
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QApplication, QMessageBox, QGroupBox,
    QCheckBox, QLineEdit, QSpinBox, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...utils.theme_manager import ThemeManager
from ...utils.version import APP_NAME, APP_VERSION
from ..widgets.page_header import PageHeader


class SettingsPage(QWidget):
    """설정 페이지"""

    theme_preset_changed = Signal(str)
    hyperlink_external_requests_enabled_changed = Signal(bool)
    hyperlink_timeout_sec_changed = Signal(int)
    hyperlink_domain_allowlist_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # 페이지 헤더
        page_header = PageHeader(
            "설정",
            "앱의 외관과 동작을 사용자 환경에 맞게 조정합니다",
            "⚙️"
        )
        layout.addWidget(page_header)

        # ── 🎨 외관 섹션 ──
        appearance_group = self._create_section_group("🎨 외관", "테마와 색상을 변경합니다")
        appearance_layout = QVBoxLayout()

        theme_row = QHBoxLayout()
        theme_label = QLabel("테마 프리셋")
        theme_label.setMinimumWidth(140)
        theme_row.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemeManager.get_presets())
        self.theme_combo.currentTextChanged.connect(self.theme_preset_changed.emit)
        self.theme_combo.setMinimumWidth(200)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()

        appearance_layout.addLayout(theme_row)
        appearance_group.layout().addLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # ── 📂 출력 섹션 ──
        output_group = self._create_section_group("📂 출력", "변환/저장 파일의 기본 출력 위치를 지정합니다")
        output_layout = QHBoxLayout()

        dir_label = QLabel("기본 출력 폴더")
        dir_label.setMinimumWidth(140)
        output_layout.addWidget(dir_label)

        self.output_label = QLabel(str(Path.home() / "Documents" / "HWP Master"))
        self.output_label.setStyleSheet(
            "color: #8b949e; background: #161b22; padding: 8px 12px; "
            "border-radius: 6px; border: 1px solid #30363d;"
        )
        output_layout.addWidget(self.output_label, 1)

        self.output_btn = QPushButton("변경...")
        self.output_btn.setProperty("class", "secondary")
        self.output_btn.setMinimumWidth(100)
        output_layout.addWidget(self.output_btn)

        output_group.layout().addLayout(output_layout)
        layout.addWidget(output_group)

        # ── 🔗 하이퍼링크 검사 섹션 ──
        hyperlink_group = self._create_section_group(
            "🔗 하이퍼링크 검사",
            "문서 내 링크 검사 시 네트워크/프라이버시 설정을 관리합니다"
        )
        hyper_layout = QVBoxLayout()

        # 외부 접속 체크박스
        self.hyperlink_external_checkbox = QCheckBox(
            "외부 사이트에 실제로 접속하여 검사 (네트워크 요청 발생)"
        )
        self.hyperlink_external_checkbox.toggled.connect(
            self.hyperlink_external_requests_enabled_changed.emit
        )
        hyper_layout.addWidget(self.hyperlink_external_checkbox)

        # 타임아웃
        timeout_row = QHBoxLayout()
        timeout_label = QLabel("타임아웃(초)")
        timeout_label.setMinimumWidth(140)
        timeout_row.addWidget(timeout_label)
        self.hyperlink_timeout_spin = QSpinBox()
        self.hyperlink_timeout_spin.setRange(1, 60)
        self.hyperlink_timeout_spin.setFixedWidth(80)
        self.hyperlink_timeout_spin.valueChanged.connect(
            self.hyperlink_timeout_sec_changed.emit
        )
        timeout_row.addWidget(self.hyperlink_timeout_spin)
        timeout_row.addStretch()
        hyper_layout.addLayout(timeout_row)

        # 도메인 allowlist
        allow_row = QHBoxLayout()
        allow_label = QLabel("도메인 allowlist")
        allow_label.setMinimumWidth(140)
        allow_row.addWidget(allow_label)
        self.hyperlink_allowlist_edit = QLineEdit()
        self.hyperlink_allowlist_edit.setPlaceholderText("example.com, *.corp.local")
        self.hyperlink_allowlist_edit.textChanged.connect(
            self.hyperlink_domain_allowlist_changed.emit
        )
        allow_row.addWidget(self.hyperlink_allowlist_edit, 1)
        hyper_layout.addLayout(allow_row)

        hint = QLabel(
            "allowlist가 비어있으면 모든 도메인에 대해 검사합니다. "
            "allowlist가 있으면 매칭되는 도메인만 접속합니다."
        )
        hint.setStyleSheet("color: #484f58; font-size: 12px;")
        hint.setWordWrap(True)
        hyper_layout.addWidget(hint)

        hyperlink_group.layout().addLayout(hyper_layout)
        layout.addWidget(hyperlink_group)

        # ── 🔧 시스템 섹션 ──
        system_group = self._create_section_group(
            "🔧 시스템",
            "프로세스 관리 및 앱 정보"
        )
        system_layout = QVBoxLayout()

        # 한글 프로세스 정리
        cleanup_row = QHBoxLayout()
        cleanup_label = QLabel("한글 프로세스 정리")
        cleanup_label.setMinimumWidth(140)
        cleanup_row.addWidget(cleanup_label)

        self.cleanup_btn = QPushButton("정리...")
        self.cleanup_btn.setProperty("class", "secondary")
        self.cleanup_btn.setMinimumWidth(100)
        self.cleanup_btn.clicked.connect(self._cleanup_hwp_process)
        cleanup_row.addWidget(self.cleanup_btn)

        cleanup_desc = QLabel("실행 중인 hwp.exe 프로세스를 강제 종료합니다")
        cleanup_desc.setStyleSheet("color: #484f58; font-size: 12px;")
        cleanup_row.addWidget(cleanup_desc, 1)
        system_layout.addLayout(cleanup_row)

        system_group.layout().addLayout(system_layout)
        layout.addWidget(system_group)

        layout.addStretch()

        # 버전 정보
        version = QApplication.applicationVersion() or APP_VERSION
        version_label = QLabel(f"{APP_NAME} v{version}")
        version_label.setStyleSheet("color: #484f58; font-size: 12px;")
        layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignCenter)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    @staticmethod
    def _create_section_group(title: str, description: str = "") -> QGroupBox:
        """아이콘 포함 섹션 QGroupBox 생성"""
        group = QGroupBox(title)
        group.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        group.setProperty("class", "settings-group")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        if description:
            desc_label = QLabel(description)
            desc_label.setProperty("class", "subtitle")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        return group

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
            proc = subprocess.run(
                ["taskkill", "/IM", "hwp.exe", "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                QMessageBox.information(self, "완료", "한글(hwp.exe) 프로세스를 종료했습니다.")
            else:
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
