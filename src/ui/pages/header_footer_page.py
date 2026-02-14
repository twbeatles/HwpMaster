"""
Header/Footer Page
헤더/푸터 관리 UI 페이지

Author: HWP Master
"""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QGroupBox,
    QGridLayout, QFrame, QCheckBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard
from ..widgets.toast import get_toast_manager
from ...utils.settings import get_settings_manager


PRESETS = {
    "공문서 스타일": {"page_format": "- {page} -", "position": "center"},
    "보고서 스타일": {"page_format": "{page}/{total}", "position": "right", "header_right": "{{filename}}"},
    "논문 스타일": {"page_format": "{page}", "position": "center", "header_center": "{{title}}"},
    "제안서 스타일": {"page_format": "{page}/{total}", "position": "right", "header_left": "{{company}}"},
}


class PresetCard(QFrame):
    """프리셋 카드"""
    clicked = Signal(str)
    
    def __init__(self, name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.name = name
        self.setObjectName("presetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(150, 70)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel(name)
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #e6edf3;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.setStyleSheet("""
            #presetCard { background: #161b22; border: 1px solid #30363d; border-radius: 10px; }
            #presetCard:hover { border-color: #8957e5; background: rgba(137, 87, 229, 0.1); }
        """)
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.name)


class HeaderFooterPage(QWidget):
    """헤더/푸터 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.worker: Any = None
        self._settings = get_settings_manager()
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # 헤더
        header = QLabel("📄 헤더/푸터 관리")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(header)
        
        desc = QLabel("페이지 번호, 문서명, 날짜 등을 일괄 삽입합니다.")
        desc.setStyleSheet("font-size: 14px; color: #8b949e;")
        layout.addWidget(desc)
        
        # 프리셋
        preset_layout = QHBoxLayout()
        for name in PRESETS.keys():
            card = PresetCard(name)
            card.clicked.connect(self._on_preset_selected)
            preset_layout.addWidget(card)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        # 설정
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(24)
        
        # 헤더 설정
        header_group = QGroupBox("헤더")
        header_layout = QGridLayout(header_group)
        
        self.header_enabled = QCheckBox("헤더 사용")
        header_layout.addWidget(self.header_enabled, 0, 0, 1, 2)
        
        header_layout.addWidget(QLabel("왼쪽:"), 1, 0)
        self.header_left = QLineEdit()
        header_layout.addWidget(self.header_left, 1, 1)
        
        header_layout.addWidget(QLabel("가운데:"), 2, 0)
        self.header_center = QLineEdit()
        header_layout.addWidget(self.header_center, 2, 1)
        
        header_layout.addWidget(QLabel("오른쪽:"), 3, 0)
        self.header_right = QLineEdit()
        header_layout.addWidget(self.header_right, 3, 1)
        
        settings_layout.addWidget(header_group)
        
        # 푸터/페이지번호 설정
        footer_group = QGroupBox("푸터 / 페이지 번호")
        footer_layout = QGridLayout(footer_group)
        
        self.footer_enabled = QCheckBox("푸터 사용")
        self.footer_enabled.setChecked(True)
        footer_layout.addWidget(self.footer_enabled, 0, 0, 1, 2)
        
        self.page_num_enabled = QCheckBox("페이지 번호")
        self.page_num_enabled.setChecked(True)
        footer_layout.addWidget(self.page_num_enabled, 1, 0, 1, 2)
        
        # 푸터 텍스트 설정
        footer_layout.addWidget(QLabel("왼쪽:"), 2, 0)
        self.footer_left = QLineEdit()
        footer_layout.addWidget(self.footer_left, 2, 1)

        footer_layout.addWidget(QLabel("가운데:"), 3, 0)
        self.footer_center = QLineEdit()
        footer_layout.addWidget(self.footer_center, 3, 1)
        
        footer_layout.addWidget(QLabel("오른쪽:"), 4, 0)
        self.footer_right = QLineEdit()
        footer_layout.addWidget(self.footer_right, 4, 1)

        # 페이지 번호 형식 콤보박스
        self.page_format = QComboBox()
        self.page_format.addItems(["단순 숫자 (1)", "전체 페이지 (1/10)", "- 쪽 번호 - (- 1 -)", "괄호 숫자 ((1))", "한글 숫자 (일)"])
        
        # 페이지 번호 위치 콤보박스
        self.page_position = QComboBox()
        self.page_position.addItems(["왼쪽", "가운데", "오른쪽"])
        self.page_position.setCurrentIndex(1)  # 기본값: 가운데

        footer_layout.addWidget(QLabel("형식:"), 6, 0)
        footer_layout.addWidget(self.page_format, 6, 1)
        
        footer_layout.addWidget(QLabel("위치:"), 7, 0)
        footer_layout.addWidget(self.page_position, 7, 1)
        
        settings_layout.addWidget(footer_group)
        
        # 파일 목록
        file_group = QGroupBox("대상 파일")
        file_layout = QVBoxLayout(file_group)
        self.file_list = FileListWidget()
        file_layout.addWidget(self.file_list)
        settings_layout.addWidget(file_group, 1)
        
        layout.addLayout(settings_layout)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.remove_btn = QPushButton("헤더/푸터 제거")
        self.remove_btn.setProperty("class", "secondary")
        self.remove_btn.clicked.connect(self._on_remove)
        btn_layout.addWidget(self.remove_btn)
        
        self.apply_btn = QPushButton("적용")
        self.apply_btn.setMinimumSize(150, 45)
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)

        # 진행률 카드 (긴 작업 UI 통일)
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        layout.addStretch()
        
    def _on_preset_selected(self, name: str) -> None:
        """프리셋 선택 시 처리"""
        preset = PRESETS.get(name)
        if not preset:
            return
            
        # 1. 초기화
        self.header_left.clear()
        self.header_center.clear()
        self.header_right.clear()
        self.footer_left.clear()
        self.footer_center.clear()
        self.footer_right.clear()
        
        # 2. 헤더 설정
        if "header_left" in preset: self.header_left.setText(preset["header_left"])
        if "header_center" in preset: self.header_center.setText(preset["header_center"])
        if "header_right" in preset: self.header_right.setText(preset["header_right"])
        
        # 3. 헤더/푸터/페이지번호 on/off
        # 프리셋에 헤더 텍스트가 있으면 헤더 활성화
        self.header_enabled.setChecked(any(k in preset for k in ["header_left", "header_center", "header_right"]))
        self.footer_enabled.setChecked(True)
        self.page_num_enabled.setChecked(True)

        # 4. 페이지 번호 포맷 매핑
        page_format = preset.get("page_format", "{page}")
        format_idx_map = {
            "{page}": 0,
            "{page}/{total}": 1,
            "- {page} -": 2,
        }
        if page_format in format_idx_map:
            self.page_format.setCurrentIndex(format_idx_map[page_format])
            
        position = preset.get("position", "center")
        if position == "left": self.page_position.setCurrentIndex(0)
        elif position == "center": self.page_position.setCurrentIndex(1)
        elif position == "right": self.page_position.setCurrentIndex(2)
        
        # 4. 알림
        get_toast_manager().info(f"프리셋 '{name}'이(가) 적용되었습니다.")

    def _on_remove(self) -> None:
        """헤더/푸터 제거"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
            
        from ...utils.worker import HeaderFooterWorker
        # 제거 시에는 config 불필요, mode="remove"
        
        # 저장 폴더 선택 (덮어쓰기 방지용, 선택 안하면 덮어쓰기?)
        # 여기서는 편의상 덮어쓰기 기본 or 사용자 선택?
        # 일반적으로는 "변환/저장" 버튼이 있으면 output_dir을 받지만, 여기선 "적용" 버튼임.
        # "적용"은 덮어쓰기를 의미하거나, 별도 설정이 있어야 함.
        # 기존 코드는 '덮어쓰기'를 암시 (result = apply(source, ... output=None))
        # 안전을 위해 output_dir 확인
        
        # 일단 덮어쓰기로 진행 (Backup 기능이 있으면 좋겠지만)
        # 사용자에게 물어보는 것이 좋음
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "확인", "원본 파일에 덮어쓰시겠습니까?\n'No'를 선택하면 별도 폴더에 저장합니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
            
        output_dir = None
        if reply == QMessageBox.StandardButton.No:
            start = self._settings.get("default_output_dir", "")
            output_dir = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", start)
            if not output_dir:
                return

        self.worker = HeaderFooterWorker("remove", files, output_dir=output_dir)
        self._run_worker()
        
    def _on_apply(self) -> None:
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
            
        # 설정 수집
        from ...core.header_footer_manager import HeaderFooterConfig, PageNumberFormat, HeaderFooterPosition
        
        config = HeaderFooterConfig()
        
        # 헤더
        config.header_enabled = self.header_enabled.isChecked()
        config.header_left = self.header_left.text()
        config.header_center = self.header_center.text()
        config.header_right = self.header_right.text()
        
        # 푸터
        config.footer_enabled = self.footer_enabled.isChecked()
        # 푸터 텍스트 설정
        config.footer_left = self.footer_left.text()
        config.footer_center = self.footer_center.text()
        config.footer_right = self.footer_right.text()
        
        # 페이지 번호
        config.page_number_enabled = self.page_num_enabled.isChecked()
        
        format_idx = self.page_format.currentIndex()
        format_map = [
            PageNumberFormat.SIMPLE, PageNumberFormat.TOTAL, 
            PageNumberFormat.DASH, PageNumberFormat.BRACKET, 
            PageNumberFormat.KOREAN
        ]
        if 0 <= format_idx < len(format_map):
            config.page_number_format = format_map[format_idx]
            
        pos_idx = self.page_position.currentIndex()
        pos_map = [
            HeaderFooterPosition.LEFT, HeaderFooterPosition.CENTER, HeaderFooterPosition.RIGHT
        ]
        if 0 <= pos_idx < len(pos_map):
            config.page_number_position = pos_map[pos_idx]
            
        # 페이지 번호 위치 (헤더/푸터) - UI에는 관련 설정이 없으므로 기본값(Footer) 사용
        config.page_number_in_footer = True 
        
        # 덮어쓰기 확인
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "확인", "원본 파일에 덮어쓰시겠습니까?\n'No'를 선택하면 별도 폴더에 저장합니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
            
        output_dir = None
        if reply == QMessageBox.StandardButton.No:
            start = self._settings.get("default_output_dir", "")
            output_dir = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", start)
            if not output_dir:
                return

        from ...utils.worker import HeaderFooterWorker
        self.worker = HeaderFooterWorker("apply", files, config, output_dir)
        self._run_worker()

    def _run_worker(self):
        if self.worker is None:
            return

        self.progress_card.setVisible(True)
        self.progress_card.reset()
        self.progress_card.set_title("헤더/푸터 작업")
        self.progress_card.set_status("작업 준비 중...")

        try:
            self.progress_card.cancelled.disconnect()
        except TypeError:
            pass

        self.progress_card.cancelled.connect(self.worker.cancel)
        self.worker.progress.connect(lambda c, t, n: (self.progress_card.set_count(c, t), self.progress_card.set_current_file(n)))
        self.worker.status_changed.connect(self.progress_card.set_status)
        self.worker.finished_with_result.connect(self._on_finished)
        self.worker.error_occurred.connect(self._on_error)

        self.worker.start()
        self.apply_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        
    def _on_progress(self, current: int, total: int, message: str) -> None:
        get_toast_manager().info(f"처리 중: {message} ({current}/{total})")
        
    def _on_finished(self, result) -> None:
        self.apply_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        
        data = getattr(result, "data", None) or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        if result.success:
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.progress_card.set_completed(success_count, fail_count)
            get_toast_manager().success(f"{success_count}개 파일 작업 완료")
        else:
            self.progress_card.set_error(getattr(result, "error_message", None) or "오류 발생")
            get_toast_manager().error(f"오류: {getattr(result, 'error_message', None)}")
            
    def _on_error(self, message: str) -> None:
        self.progress_card.set_error(message)
        get_toast_manager().error(f"작업 중 오류 발생: {message}")

