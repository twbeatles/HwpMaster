"""
Table Doctor Page
표 주치의 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QComboBox,
    QDoubleSpinBox, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...core.table_doctor import TableDoctor, TableStyle
from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader
from ...utils.worker import TableDoctorWorker, WorkerResult
from ...utils.settings import get_settings_manager


class TableStyleCard(QFrame):
    """표 스타일 프리셋 카드"""
    
    clicked = Signal(str)
    
    def __init__(
        self,
        preset_id: str,
        style: TableStyle,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.preset_id = preset_id
        self.table_style = style
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(110)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        
        name_label = QLabel(f"📊 {style.name}")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        spec_text = f"테두리 {style.border_width}mm, 여백 {style.cell_padding_left}mm"
        spec_label = QLabel(spec_text)
        spec_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(spec_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.preset_id)
        super().mousePressEvent(event)


class TableDoctorPage(QWidget):
    """Table Doctor 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._table_doctor = TableDoctor()
        self._selected_style: Optional[TableStyle] = None
        self._worker: Optional[TableDoctorWorker] = None
        self._settings = get_settings_manager()
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 헤더
        header = PageHeader(
            "표 도우미",
            "깨지거나 제멋대로인 표의 테두리, 셀 여백을 규정에 맞게 치료합니다",
            "🩺"
        )
        layout.addWidget(header)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)
        
        # 왼쪽: 스타일 선택
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        
        preset_group = QGroupBox("📊 표 스타일 프리셋")
        preset_layout = QGridLayout(preset_group)
        preset_layout.setSpacing(8)
        
        presets = list(self._table_doctor.PRESETS.items())
        cols = 2
        for idx, (preset_id, style) in enumerate(presets):
            card = TableStyleCard(preset_id, style)
            card.clicked.connect(self._on_preset_selected)
            row = idx // cols
            col = idx % cols
            preset_layout.addWidget(card, row, col)
        
        left_panel.addWidget(preset_group)
        
        # 커스텀 설정
        custom_group = QGroupBox("✏️ 커스텀 설정")
        custom_layout = QGridLayout(custom_group)
        
        custom_layout.addWidget(QLabel("테두리 두께 (mm):"), 0, 0)
        self.border_spin = QDoubleSpinBox()
        self.border_spin.setRange(0.1, 2.0)
        self.border_spin.setValue(0.4)
        self.border_spin.setSingleStep(0.1)
        custom_layout.addWidget(self.border_spin, 0, 1)
        
        custom_layout.addWidget(QLabel("셀 여백 (mm):"), 1, 0)
        self.padding_spin = QDoubleSpinBox()
        self.padding_spin.setRange(0.5, 5.0)
        self.padding_spin.setValue(2.0)
        self.padding_spin.setSingleStep(0.5)
        custom_layout.addWidget(self.padding_spin, 1, 1)
        
        apply_custom_btn = QPushButton("커스텀 적용")
        apply_custom_btn.clicked.connect(self._apply_custom)
        custom_layout.addWidget(apply_custom_btn, 2, 0, 1, 2)
        
        left_panel.addWidget(custom_group)
        
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
        
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        right_panel.addWidget(self.progress_card)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.scan_btn = QPushButton("표 스캔")
        self.scan_btn.setProperty("class", "secondary")
        self.scan_btn.clicked.connect(self._scan_tables)
        btn_layout.addWidget(self.scan_btn)
        
        self.apply_btn = QPushButton("스타일 적용")
        self.apply_btn.setMinimumWidth(120)
        self.apply_btn.clicked.connect(self._apply_style)
        btn_layout.addWidget(self.apply_btn)
        
        right_panel.addLayout(btn_layout)
        
        main_layout.addLayout(right_panel, stretch=1)
        
        layout.addLayout(main_layout)
    
    def _on_preset_selected(self, preset_id: str) -> None:
        style = self._table_doctor.get_preset(preset_id)
        if style:
            self._selected_style = style
            self.selected_label.setText(
                f"✅ 선택된 스타일: {style.name}\n"
                f"   테두리 {style.border_width}mm, 여백 {style.cell_padding_left}mm"
            )
            self.border_spin.setValue(style.border_width)
            self.padding_spin.setValue(style.cell_padding_left)
    
    def _apply_custom(self) -> None:
        self._selected_style = self._table_doctor.create_custom_style(
            name="커스텀",
            border_width=self.border_spin.value(),
            cell_padding=self.padding_spin.value()
        )
        self.selected_label.setText(
            f"✅ 선택된 스타일: 커스텀\n"
            f"   테두리 {self._selected_style.border_width}mm, "
            f"여백 {self._selected_style.cell_padding_left}mm"
        )
    
    def _scan_tables(self) -> None:
        files = self.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "오류", "스캔할 파일을 추가해주세요.")
            return
        
        tables = self._table_doctor.scan_tables(files[0])
        
        if tables:
            msg = f"📊 표 스캔 결과\n\n발견된 표: {len(tables)}개\n\n"
            for t in tables[:5]:
                msg += f"• 표 {t.index + 1}: {t.row_count}행 × {t.col_count}열\n"
            if len(tables) > 5:
                msg += f"... 외 {len(tables) - 5}개"
        else:
            msg = "문서에서 표를 찾을 수 없습니다."
        
        QMessageBox.information(self, "스캔 결과", msg)
    
    def _apply_style(self) -> None:
        files = self.file_list.get_files()
        
        if not files:
            QMessageBox.warning(self, "오류", "대상 파일을 추가해주세요.")
            return
        
        if not self._selected_style:
            QMessageBox.warning(self, "오류", "표 스타일을 선택해주세요.")
            return
        
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "저장 위치 선택",
            self._settings.get("default_output_dir", str(Path.home() / "Documents"))
        )
        
        if not output_dir:
            return
        
        self.progress_card.setVisible(True)
        self.progress_card.set_status("표 스타일 적용 중...")
        self.progress_card.reset()
        self.apply_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        
        if self._worker is not None:
            try:
                self.progress_card.cancelled.disconnect(self._worker.cancel)
            except TypeError:
                pass

        self._worker = TableDoctorWorker(files, self._selected_style, output_dir)
        self.progress_card.cancelled.connect(self._worker.cancel)
        self._worker.progress.connect(lambda c, t, n: (self.progress_card.set_count(c, t), self.progress_card.set_current_file(n)))
        self._worker.status_changed.connect(self.progress_card.set_status)
        self._worker.finished_with_result.connect(self._on_apply_finished)
        self._worker.error_occurred.connect(self._on_apply_error)
        self._worker.start()

    def _on_apply_finished(self, result: WorkerResult) -> None:
        self.apply_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)

        data = result.data or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        if result.success:
            success = data.get("success_count", 0)
            fail = data.get("fail_count", 0)
            tables_fixed = data.get("tables_fixed", 0)
            out_dir = data.get("output_dir", "")
            self.progress_card.set_completed(success, fail)
            QMessageBox.information(
                self,
                "완료",
                f"표 스타일 적용이 완료되었습니다.\n\n"
                f"처리 파일: {success + fail}개\n"
                f"수정된 표: {tables_fixed}개\n"
                f"저장 위치: {out_dir}"
            )
        else:
            self.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "표 스타일 적용 중 오류가 발생했습니다.")

    def _on_apply_error(self, message: str) -> None:
        self.apply_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.progress_card.set_error(message)
