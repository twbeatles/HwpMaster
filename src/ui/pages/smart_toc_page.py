"""
Smart TOC Page
목차 생성기 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QTreeWidget,
    QTreeWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ...core.smart_toc import SmartTOC, TocEntry


class SmartTocPage(QWidget):
    """Smart TOC 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._smart_toc = SmartTOC()
        self._file_path: Optional[str] = None
        self._last_result = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        title = QLabel("📑 자동 목차")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("글자 크기와 패턴을 분석하여 자동으로 목차를 추출합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        # 파일 선택
        file_group = QGroupBox("📄 대상 파일")
        file_layout = QHBoxLayout(file_group)
        
        self.file_label = QLabel("파일을 선택하세요")
        self.file_label.setStyleSheet("color: #888888;")
        file_layout.addWidget(self.file_label, 1)
        
        file_btn = QPushButton("파일 선택...")
        file_btn.clicked.connect(self._select_file)
        file_layout.addWidget(file_btn)
        
        layout.addWidget(file_group)
        
        # 목차 미리보기
        toc_group = QGroupBox("📑 추출된 목차")
        toc_layout = QVBoxLayout(toc_group)
        
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabels(["제목", "수준", "줄"])
        self.toc_tree.setColumnWidth(0, 400)
        self.toc_tree.setColumnWidth(1, 60)
        self.toc_tree.setColumnWidth(2, 60)
        self.toc_tree.setMinimumHeight(300)
        toc_layout.addWidget(self.toc_tree)
        
        # 통계
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #888888;")
        toc_layout.addWidget(self.stats_label)
        
        layout.addWidget(toc_group)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.extract_btn = QPushButton("목차 추출")
        self.extract_btn.clicked.connect(self._extract_toc)
        btn_layout.addWidget(self.extract_btn)
        
        self.save_btn = QPushButton("목차 저장")
        self.save_btn.setProperty("class", "secondary")
        self.save_btn.clicked.connect(self._save_toc)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)
        
        self.insert_btn = QPushButton("문서에 삽입")
        self.insert_btn.clicked.connect(self._insert_toc)
        self.insert_btn.setEnabled(False)
        btn_layout.addWidget(self.insert_btn)
        
        layout.addLayout(btn_layout)
    
    def _select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "파일 선택", "", "HWP 파일 (*.hwp *.hwpx)"
        )
        if file_path:
            self._file_path = file_path
            self.file_label.setText(f"✅ {Path(file_path).name}")
            self.file_label.setStyleSheet("color: #28a745;")
    
    def _extract_toc(self) -> None:
        if not self._file_path:
            QMessageBox.warning(self, "오류", "파일을 선택해주세요.")
            return
        
        result = self._smart_toc.extract_toc(self._file_path)
        self._last_result = result
        
        if not result.success:
            QMessageBox.warning(self, "오류", f"목차 추출 실패:\n{result.error_message}")
            return
        
        # 트리 표시
        self.toc_tree.clear()
        
        for entry in result.entries:
            item = QTreeWidgetItem([
                entry.text,
                f"H{entry.level}",
                str(entry.line_number)
            ])
            self.toc_tree.addTopLevelItem(item)
        
        # 통계
        h1 = len(result.get_by_level(1))
        h2 = len(result.get_by_level(2))
        h3 = len(result.get_by_level(3))
        
        self.stats_label.setText(
            f"총 {result.total_entries}개 항목 (H1: {h1}, H2: {h2}, H3: {h3})"
        )
        
        self.save_btn.setEnabled(True)
        self.insert_btn.setEnabled(True)
        
        if result.total_entries == 0:
            QMessageBox.information(self, "알림", "문서에서 목차 항목을 찾지 못했습니다.")
    
    def _save_toc(self) -> None:
        if not self._last_result:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "목차 저장",
            str(Path.home() / "Documents" / "toc.txt"),
            "텍스트 파일 (*.txt);;HTML 파일 (*.html)"
        )
        
        if file_path:
            fmt = "html" if file_path.endswith(".html") else "txt"
            if self._smart_toc.save_toc_as_file(self._last_result, file_path, fmt):
                QMessageBox.information(self, "완료", f"목차가 저장되었습니다:\n{file_path}")
            else:
                QMessageBox.warning(self, "오류", "목차 저장에 실패했습니다.")
    
    def _insert_toc(self) -> None:
        if not self._file_path or not self._last_result:
            return
        
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "저장 위치",
            str(Path(self._file_path).parent / f"TOC_{Path(self._file_path).name}"),
            "HWP 파일 (*.hwp)"
        )
        
        if output_path:
            if self._smart_toc.generate_toc_hwp(self._file_path, output_path):
                QMessageBox.information(
                    self,
                    "완료",
                    f"목차가 삽입된 문서가 저장되었습니다:\n{output_path}"
                )
            else:
                QMessageBox.warning(self, "오류", "목차 삽입에 실패했습니다.")
