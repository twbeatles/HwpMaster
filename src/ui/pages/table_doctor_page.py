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
        self.style = style
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        
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
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        title = QLabel("🩺 표 도우미")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("깨지거나 제멋대로인 표의 테두리, 셀 여백을 규정에 맞게 치료합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
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
            str(Path.home() / "Documents")
        )
        
        if not output_dir:
            return
        
        self.progress_card.setVisible(True)
        self.progress_card.set_status("표 스타일 적용 중...")
        
        try:
            results = self._table_doctor.batch_apply_style(
                files,
                self._selected_style,
                output_dir,
                progress_callback=lambda c, t, n: self.progress_card.set_count(c, t)
            )
            
            total_tables = sum(r.tables_fixed for r in results)
            success = sum(1 for r in results if r.success)
            
            self.progress_card.set_completed(success, len(results) - success)
            
            QMessageBox.information(
                self,
                "완료",
                f"표 스타일 적용이 완료되었습니다.\n\n"
                f"처리 파일: {len(results)}개\n"
                f"수정된 표: {total_tables}개\n"
                f"저장 위치: {output_dir}"
            )
            
        except Exception as e:
            self.progress_card.set_error(str(e))
            QMessageBox.warning(self, "오류", f"표 스타일 적용 중 오류:\n{e}")
