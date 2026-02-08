"""
Image Extractor Page
이미지 추출 UI 페이지

Author: HWP Master
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QProgressBar,
    QListWidget, QListWidgetItem, QFileDialog
)
from PySide6.QtCore import Qt

from ..widgets.file_list import FileListWidget
from ..widgets.toast import get_toast_manager


class ImageExtractorPage(QWidget):
    """이미지 추출 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._output_dir = ""
        self.worker = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # 헤더
        header = QLabel("🖼️ 이미지 추출")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(header)
        
        desc = QLabel("문서 내 모든 이미지를 개별 파일로 추출합니다.")
        desc.setStyleSheet("font-size: 14px; color: #8b949e;")
        layout.addWidget(desc)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)
        
        # 파일 선택
        file_group = QGroupBox("문서 선택")
        file_layout = QVBoxLayout(file_group)
        self.file_list = FileListWidget()
        file_layout.addWidget(self.file_list)
        main_layout.addWidget(file_group)
        
        # 설정 및 결과
        right_layout = QVBoxLayout()
        
        # 출력 설정
        output_group = QGroupBox("출력 설정")
        output_layout = QVBoxLayout(output_group)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("저장 폴더:"))
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.dir_input.setPlaceholderText("폴더 선택...")
        dir_layout.addWidget(self.dir_input)
        self.browse_btn = QPushButton("찾아보기")
        self.browse_btn.clicked.connect(self._on_browse)
        dir_layout.addWidget(self.browse_btn)
        output_layout.addLayout(dir_layout)
        
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("파일명 접두사:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("(선택사항)")
        prefix_layout.addWidget(self.prefix_input)
        output_layout.addLayout(prefix_layout)
        
        right_layout.addWidget(output_group)
        
        # 진행률
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right_layout.addWidget(self.progress)
        
        # 결과 목록
        result_group = QGroupBox("추출된 이미지")
        result_layout = QVBoxLayout(result_group)
        
        self.result_list = QListWidget()
        result_layout.addWidget(self.result_list)
        
        self.result_label = QLabel("추출된 이미지: 0개")
        self.result_label.setStyleSheet("color: #8b949e;")
        result_layout.addWidget(self.result_label)
        
        right_layout.addWidget(result_group, 1)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.open_folder_btn = QPushButton("폴더 열기")
        self.open_folder_btn.setProperty("class", "secondary")
        self.open_folder_btn.setEnabled(False)
        btn_layout.addWidget(self.open_folder_btn)
        
        self.extract_btn = QPushButton("이미지 추출")
        self.extract_btn.setMinimumSize(150, 45)
        self.extract_btn.clicked.connect(self._on_extract)
        btn_layout.addWidget(self.extract_btn)
        
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout, 1)
        
        layout.addLayout(main_layout)
    
    def _on_browse(self) -> None:
        """폴더 선택"""
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if folder:
            self._output_dir = folder
            self.dir_input.setText(folder)
    
    def _on_extract(self) -> None:
        """이미지 추출"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
        
        if not self._output_dir:
            get_toast_manager().warning("저장 폴더를 선택해주세요.")
            return
        
        self.result_list.clear()
        self.progress.setVisible(True)
        self.progress.setValue(0)
        get_toast_manager().info("이미지 추출 중...")
        
        # 데모 데이터
        # Worker 설정
        from ...utils.worker import ImageExtractWorker
        
        prefix = self.prefix_input.text().strip()
        
        self.worker = ImageExtractWorker(files, self._output_dir, prefix)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_with_result.connect(self._on_finished)
        self.worker.error_occurred.connect(self._on_error)
        
        self.worker.start()
        
        # UI 잠금
        self.extract_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
    
    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress.setValue(int(current / total * 100))
        self.result_label.setText(f"처리 중: {message}")
    
    def _on_finished(self, result) -> None:
        self.progress.setVisible(False)
        self.extract_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)
        
        if result.success:
            count = result.data.get("success_count", 0)
            images = result.data.get("total_images", 0)
            get_toast_manager().success(f"{count}개 파일에서 {images}개 이미지 추출 완료")
            self.result_label.setText(f"총 추출된 이미지: {images}개")
            
            # 결과 목록 업데이트 (간략히 성공 메시지만)
            self.result_list.clear()
            self.result_list.addItem(QListWidgetItem(f"완료: {count}개 파일 처리됨"))
        else:
            get_toast_manager().error(f"오류: {result.error_message}")
            
    def _on_error(self, message: str) -> None:
        get_toast_manager().error(f"작업 중 오류 발생: {message}")

