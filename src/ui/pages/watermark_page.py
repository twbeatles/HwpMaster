"""
Watermark Page
워터마크 삽입 UI 페이지

Author: HWP Master
"""

from typing import Any, Mapping, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QSlider,
    QComboBox, QGroupBox, QGridLayout, QFrame,
    QRadioButton, QButtonGroup, QFileDialog, QStackedWidget
)
from PySide6.QtCore import Qt, Signal

from ..widgets.file_list import FileListWidget
from ..widgets.toast import get_toast_manager, ToastType


# 프리셋 정의
WATERMARK_PRESETS = {
    "대외비": {"text": "대외비", "color": "#ff0000", "opacity": 25},
    "DRAFT": {"text": "DRAFT", "color": "#888888", "opacity": 20},
    "CONFIDENTIAL": {"text": "CONFIDENTIAL", "color": "#cc0000", "opacity": 25},
    "SAMPLE": {"text": "SAMPLE", "color": "#0066cc", "opacity": 30},
    "사본": {"text": "사본", "color": "#666666", "opacity": 25},
    "무단복제금지": {"text": "무단복제금지", "color": "#990000", "opacity": 20},
}


class PresetCard(QFrame):
    """프리셋 카드"""
    clicked = Signal(str)
    
    def __init__(self, name: str, config: Mapping[str, object], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.name = name
        self.setObjectName("presetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(140, 80)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel(name)
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {config.get('color', '#888')};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        opacity = QLabel(f"투명도: {config.get('opacity', 25)}%")
        opacity.setStyleSheet("font-size: 11px; color: #8b949e;")
        opacity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(opacity)
        
        self.setStyleSheet("""
            #presetCard {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
            #presetCard:hover {
                border-color: #8957e5;
                background: rgba(137, 87, 229, 0.1);
            }
        """)
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.name)


class WatermarkPage(QWidget):
    """워터마크 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.worker: Any = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # 헤더
        header = QLabel("💧 워터마크")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(header)
        
        desc = QLabel("문서에 텍스트 또는 이미지 워터마크를 일괄 삽입합니다.")
        desc.setStyleSheet("font-size: 14px; color: #8b949e;")
        layout.addWidget(desc)
        
        # 프리셋 섹션
        preset_group = QGroupBox("빠른 프리셋")
        preset_layout = QHBoxLayout(preset_group)
        preset_layout.setSpacing(12)
        
        for name, config in WATERMARK_PRESETS.items():
            card = PresetCard(name, config)
            card.clicked.connect(self._on_preset_selected)
            preset_layout.addWidget(card)
        
        preset_layout.addStretch()
        layout.addWidget(preset_group)
        
        # 설정 섹션
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(24)
        
        # 텍스트 설정
        text_group = QGroupBox("워터마크 설정")
        text_layout = QGridLayout(text_group)
        
        # 타입 선택
        type_layout = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.radio_text = QRadioButton("텍스트")
        self.radio_image = QRadioButton("이미지")
        self.radio_text.setChecked(True)
        self.type_group.addButton(self.radio_text, 0)
        self.type_group.addButton(self.radio_image, 1)
        self.type_group.idToggled.connect(self._on_type_changed)
        
        type_layout.addWidget(QLabel("유형:"))
        type_layout.addWidget(self.radio_text)
        type_layout.addWidget(self.radio_image)
        type_layout.addStretch()
        text_layout.addLayout(type_layout, 0, 0, 1, 2)
        
        # 스택 위젯 (텍스트/이미지 설정 전환)
        self.stack = QStackedWidget()
        
        # 1. 텍스트 설정 페이지
        text_page = QWidget()
        text_page_layout = QGridLayout(text_page)
        text_page_layout.setContentsMargins(0, 0, 0, 0)
        
        text_page_layout.addWidget(QLabel("워터마크 텍스트:"), 0, 0)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("워터마크 텍스트 입력")
        text_page_layout.addWidget(self.text_input, 0, 1)
        
        text_page_layout.addWidget(QLabel("글자 크기:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 120)
        self.font_size_spin.setValue(48)
        text_page_layout.addWidget(self.font_size_spin, 1, 1)
        
        self.stack.addWidget(text_page)
        
        # 2. 이미지 설정 페이지
        image_page = QWidget()
        image_page_layout = QGridLayout(image_page)
        image_page_layout.setContentsMargins(0, 0, 0, 0)
        
        image_page_layout.addWidget(QLabel("이미지 경로:"), 0, 0)
        file_select_layout = QHBoxLayout()
        self.image_path_input = QLineEdit()
        self.image_path_input.setPlaceholderText("이미지 파일을 선택하세요")
        self.image_select_btn = QPushButton("찾기...")
        self.image_select_btn.clicked.connect(self._select_image_file)
        file_select_layout.addWidget(self.image_path_input)
        file_select_layout.addWidget(self.image_select_btn)
        image_page_layout.addLayout(file_select_layout, 0, 1)
        
        self.stack.addWidget(image_page)
        
        text_layout.addWidget(self.stack, 1, 0, 1, 2)
        
        # 공통 설정 (투명도, 회전)
        text_layout.addWidget(QLabel("투명도:"), 2, 0)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 80)
        self.opacity_slider.setValue(25)
        text_layout.addWidget(self.opacity_slider, 2, 1)
        
        text_layout.addWidget(QLabel("회전 각도:"), 3, 0)
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(-180, 180)
        self.rotation_spin.setValue(-45)
        text_layout.addWidget(self.rotation_spin, 3, 1)
        
        settings_layout.addWidget(text_group)
        
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
        
        self.remove_btn = QPushButton("워터마크 제거")
        self.remove_btn.setProperty("class", "secondary")
        self.remove_btn.clicked.connect(self._on_remove)
        btn_layout.addWidget(self.remove_btn)
        
        self.apply_btn = QPushButton("워터마크 적용")
        self.apply_btn.setMinimumSize(150, 45)
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
    def _on_preset_selected(self, name: str) -> None:
        """프리셋 선택 시 처리"""
        config = WATERMARK_PRESETS.get(name)
        if not config:
            return
            
        # 1. 텍스트 모드로 전환
        self.radio_text.setChecked(True)
        self.stack.setCurrentIndex(0)
        
        # 2. 값 설정
        text_value = str(config.get("text", ""))
        opacity_value = int(config.get("opacity", 25))
        self.text_input.setText(text_value)
        self.opacity_slider.setValue(opacity_value)
        
        # 3. 알림
        get_toast_manager().info(f"프리셋 '{name}'이(가) 적용되었습니다.")

    def _on_type_changed(self, id: int):
        self.stack.setCurrentIndex(id)
        
    def _select_image_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.image_path_input.setText(file_path)

    def _on_remove(self) -> None:
        """워터마크 제거"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
            
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "확인", "원본 파일에 덮어쓰시겠습니까?\n'No'를 선택하면 별도 폴더에 저장합니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
            
        output_dir = None
        if reply == QMessageBox.StandardButton.No:
            output_dir = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택")
            if not output_dir:
                return

        from ...utils.worker import WatermarkWorker
        self.worker = WatermarkWorker("remove", files, output_dir=output_dir)
        self._run_worker()
        
    def _on_apply(self) -> None:
        """워터마크 적용"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
        
        from ...core.watermark_manager import WatermarkConfig, WatermarkType
        
        is_text = self.radio_text.isChecked()
        watermark_type = WatermarkType.TEXT if is_text else WatermarkType.IMAGE
        
        text = self.text_input.text().strip()
        image_path = self.image_path_input.text().strip()
        
        if is_text and not text:
            get_toast_manager().warning("워터마크 텍스트를 입력해주세요.")
            return
            
        if not is_text and not image_path:
            get_toast_manager().warning("이미지 파일을 선택해주세요.")
            return

        config = WatermarkConfig(
            watermark_type=watermark_type,
            text=text,
            image_path=image_path,
            font_size=self.font_size_spin.value(),
            opacity=self.opacity_slider.value(),
            rotation=self.rotation_spin.value()
        )
        
        # 덮어쓰기 확인
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "확인", "원본 파일에 덮어쓰시겠습니까?\n'No'를 선택하면 별도 폴더에 저장합니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
            
        output_dir = None
        if reply == QMessageBox.StandardButton.No:
            output_dir = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택")
            if not output_dir:
                return

        from ...utils.worker import WatermarkWorker
        self.worker = WatermarkWorker("apply", files, config, output_dir)
        self._run_worker()
        
    def _run_worker(self) -> None:
        if self.worker is None:
            return
        self.worker.progress.connect(self._on_progress)
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
        
        if result.success:
            count = result.data.get("success_count", 0)
            get_toast_manager().success(f"{count}개 파일 작업 완료")
        else:
            get_toast_manager().error(f"오류: {result.error_message}")
            
    def _on_error(self, message: str) -> None:
        get_toast_manager().error(f"작업 중 오류 발생: {message}")

