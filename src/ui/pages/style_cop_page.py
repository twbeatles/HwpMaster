"""
Style Cop Page
서식 경찰 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QComboBox,
    QDoubleSpinBox, QLineEdit, QGroupBox,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...core.style_cop import StyleCop, StyleRule
from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader
from ...utils.worker import StyleCopWorker, WorkerResult
from ...utils.settings import get_settings_manager


class PresetCard(QFrame):
    """프리셋 카드"""
    
    clicked = Signal(str)
    
    def __init__(
        self,
        preset_id: str,
        rule: StyleRule,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.preset_id = preset_id
        self.rule = rule
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(110)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        
        # 이름
        name_label = QLabel(f"📋 {rule.name}")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        # 스펙
        spec_text = f"{rule.font_name} {rule.font_size}pt, 줄간격 {rule.line_spacing}%"
        spec_label = QLabel(spec_text)
        spec_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(spec_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.preset_id)
        super().mousePressEvent(event)


class StyleCopPage(QWidget):
    """Style Cop 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._style_cop = StyleCop()
        self._selected_rule: Optional[StyleRule] = None
        self._worker: Optional[StyleCopWorker] = None
        self._settings = get_settings_manager()
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 헤더
        header = PageHeader(
            "서식 도우미",
            "문서의 폰트, 크기, 줄간격을 규정에 맞게 일괄 통일합니다",
            "👮"
        )
        layout.addWidget(header)
        
        # 메인 영역 (2컬럼)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)
        
        # 왼쪽: 프리셋 + 커스텀
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        
        # 프리셋 섹션
        preset_group = QGroupBox("📋 스타일 프리셋")
        preset_layout = QGridLayout(preset_group)
        preset_layout.setSpacing(8)
        
        presets = list(self._style_cop.PRESETS.items())
        cols = 2
        for idx, (preset_id, rule) in enumerate(presets):
            card = PresetCard(preset_id, rule)
            card.clicked.connect(self._on_preset_selected)
            row = idx // cols
            col = idx % cols
            preset_layout.addWidget(card, row, col)
        
        left_panel.addWidget(preset_group)
        
        # 커스텀 설정
        custom_group = QGroupBox("✏️ 커스텀 설정")
        custom_layout = QGridLayout(custom_group)
        
        custom_layout.addWidget(QLabel("폰트:"), 0, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItems(["맑은 고딕", "바탕", "돋움", "굴림", "나눔고딕"])
        custom_layout.addWidget(self.font_combo, 0, 1)
        
        custom_layout.addWidget(QLabel("크기 (pt):"), 1, 0)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(6.0, 72.0)
        self.size_spin.setValue(11.0)
        self.size_spin.setSingleStep(0.5)
        custom_layout.addWidget(self.size_spin, 1, 1)
        
        custom_layout.addWidget(QLabel("줄간격 (%):"), 2, 0)
        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(100.0, 300.0)
        self.spacing_spin.setValue(160.0)
        self.spacing_spin.setSingleStep(10.0)
        custom_layout.addWidget(self.spacing_spin, 2, 1)
        
        apply_custom_btn = QPushButton("커스텀 적용")
        apply_custom_btn.clicked.connect(self._apply_custom)
        custom_layout.addWidget(apply_custom_btn, 3, 0, 1, 2)
        
        left_panel.addWidget(custom_group)
        
        # 선택된 규칙 표시
        self.selected_label = QLabel("선택된 스타일: 없음")
        self.selected_label.setStyleSheet("""
            background-color: #16213e;
            padding: 12px;
            border-radius: 8px;
            font-weight: bold;
        """)
        left_panel.addWidget(self.selected_label)
        
        main_layout.addLayout(left_panel, stretch=1)
        
        # 오른쪽: 파일 목록
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)
        
        files_group = QGroupBox("📁 대상 파일")
        files_layout = QVBoxLayout(files_group)
        
        self.file_list = FileListWidget()
        files_layout.addWidget(self.file_list)
        
        right_panel.addWidget(files_group)
        
        # 진행률
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        right_panel.addWidget(self.progress_card)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.check_btn = QPushButton("검사")
        self.check_btn.setProperty("class", "secondary")
        self.check_btn.clicked.connect(self._check_style)
        btn_layout.addWidget(self.check_btn)
        
        self.apply_btn = QPushButton("스타일 적용")
        self.apply_btn.setMinimumWidth(120)
        self.apply_btn.clicked.connect(self._apply_style)
        btn_layout.addWidget(self.apply_btn)
        
        right_panel.addLayout(btn_layout)
        
        main_layout.addLayout(right_panel, stretch=1)
        
        layout.addLayout(main_layout)
    
    def _on_preset_selected(self, preset_id: str) -> None:
        """프리셋 선택"""
        rule = self._style_cop.get_preset(preset_id)
        if rule:
            self._selected_rule = rule
            self.selected_label.setText(
                f"✅ 선택된 스타일: {rule.name}\n"
                f"   {rule.font_name} {rule.font_size}pt, 줄간격 {rule.line_spacing}%"
            )
            
            # 커스텀 UI 업데이트
            idx = self.font_combo.findText(rule.font_name)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
            self.size_spin.setValue(rule.font_size)
            self.spacing_spin.setValue(rule.line_spacing)
    
    def _apply_custom(self) -> None:
        """커스텀 스타일 적용"""
        self._selected_rule = StyleRule(
            name="커스텀",
            font_name=self.font_combo.currentText(),
            font_size=self.size_spin.value(),
            line_spacing=self.spacing_spin.value()
        )
        self.selected_label.setText(
            f"✅ 선택된 스타일: 커스텀\n"
            f"   {self._selected_rule.font_name} {self._selected_rule.font_size}pt, "
            f"줄간격 {self._selected_rule.line_spacing}%"
        )
    
    def _check_style(self) -> None:
        """스타일 검사"""
        files = self.file_list.get_files()
        
        if not files:
            QMessageBox.warning(self, "오류", "검사할 파일을 추가해주세요.")
            return
        
        if not self._selected_rule:
            QMessageBox.warning(self, "오류", "스타일 프리셋을 선택해주세요.")
            return
        
        # 첫 번째 파일만 검사 (미리보기)
        result = self._style_cop.check_style(files[0], self._selected_rule)
        
        msg = f"📊 스타일 검사 결과\n\n"
        msg += f"총 문단: {result.total_paragraphs}개\n"
        msg += f"폰트 불일치: {result.inconsistent_fonts}개\n"
        msg += f"크기 불일치: {result.inconsistent_sizes}개\n"
        msg += f"줄간격 불일치: {result.inconsistent_spacing}개\n"
        msg += f"\n규정 준수율: {result.compliance_score:.1f}%"
        
        QMessageBox.information(self, "검사 결과", msg)
    
    def _apply_style(self) -> None:
        """스타일 적용"""
        files = self.file_list.get_files()
        
        if not files:
            QMessageBox.warning(self, "오류", "대상 파일을 추가해주세요.")
            return
        
        if not self._selected_rule:
            QMessageBox.warning(self, "오류", "스타일 프리셋을 선택해주세요.")
            return
        
        # 출력 디렉토리 선택
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "저장 위치 선택",
            self._settings.get("default_output_dir", str(Path.home() / "Documents"))
        )
        
        if not output_dir:
            return
        
        self.progress_card.setVisible(True)
        self.progress_card.set_status("스타일 적용 중...")
        self.progress_card.reset()
        self.apply_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        
        if self._worker is not None:
            try:
                self.progress_card.cancelled.disconnect(self._worker.cancel)
            except TypeError:
                pass

        self._worker = StyleCopWorker(files, self._selected_rule, output_dir)
        self.progress_card.cancelled.connect(self._worker.cancel)
        self._worker.progress.connect(lambda c, t, n: (self.progress_card.set_count(c, t), self.progress_card.set_current_file(n)))
        self._worker.status_changed.connect(self.progress_card.set_status)
        self._worker.finished_with_result.connect(self._on_apply_finished)
        self._worker.error_occurred.connect(self._on_apply_error)
        self._worker.start()

    def _on_apply_finished(self, result: WorkerResult) -> None:
        self.apply_btn.setEnabled(True)
        self.check_btn.setEnabled(True)

        data = result.data or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        if result.success:
            success = data.get("success_count", 0)
            fail = data.get("fail_count", 0)
            out_dir = data.get("output_dir", "")
            self.progress_card.set_completed(success, fail)
            QMessageBox.information(
                self,
                "완료",
                f"스타일 적용이 완료되었습니다.\n\n"
                f"성공: {success}개\n"
                f"실패: {fail}개\n"
                f"저장 위치: {out_dir}"
            )
        else:
            self.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "스타일 적용 중 오류가 발생했습니다.")

    def _on_apply_error(self, message: str) -> None:
        self.apply_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.progress_card.set_error(message)
