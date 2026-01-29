"""
Doc Diff Page
문서 비교기 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ...core.doc_diff import DocDiff, ChangeType


class DocDiffPage(QWidget):
    """Doc Diff 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._doc_diff = DocDiff()
        self._file1_path: Optional[str] = None
        self._file2_path: Optional[str] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        title = QLabel("📊 문서 비교")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("수정 전후 파일의 텍스트 차이점을 분석하여 리포트를 생성합니다")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        # 파일 선택 영역
        files_layout = QHBoxLayout()
        files_layout.setSpacing(20)
        
        # 파일 1
        file1_group = QGroupBox("📄 원본 파일 (v1)")
        file1_layout = QVBoxLayout(file1_group)
        
        self.file1_label = QLabel("파일을 선택하세요")
        self.file1_label.setStyleSheet("color: #888888; padding: 20px;")
        self.file1_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file1_layout.addWidget(self.file1_label)
        
        file1_btn = QPushButton("파일 선택...")
        file1_btn.clicked.connect(self._select_file1)
        file1_layout.addWidget(file1_btn)
        
        files_layout.addWidget(file1_group)
        
        # 화살표
        arrow_label = QLabel("→")
        arrow_label.setFont(QFont("Segoe UI", 32))
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        files_layout.addWidget(arrow_label)
        
        # 파일 2
        file2_group = QGroupBox("📄 수정 파일 (v2)")
        file2_layout = QVBoxLayout(file2_group)
        
        self.file2_label = QLabel("파일을 선택하세요")
        self.file2_label.setStyleSheet("color: #888888; padding: 20px;")
        self.file2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file2_layout.addWidget(self.file2_label)
        
        file2_btn = QPushButton("파일 선택...")
        file2_btn.clicked.connect(self._select_file2)
        file2_layout.addWidget(file2_btn)
        
        files_layout.addWidget(file2_group)
        
        layout.addLayout(files_layout)
        
        # 결과 표시 영역
        result_group = QGroupBox("📊 비교 결과")
        result_layout = QVBoxLayout(result_group)
        
        # 통계
        self.stats_label = QLabel("파일을 선택하고 '비교 실행' 버튼을 클릭하세요")
        self.stats_label.setStyleSheet("""
            background-color: #16213e;
            padding: 16px;
            border-radius: 8px;
        """)
        result_layout.addWidget(self.stats_label)
        
        # 변경 내역
        self.diff_text = QTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setFont(QFont("Consolas", 10))
        self.diff_text.setMinimumHeight(200)
        self.diff_text.setPlaceholderText("비교 결과가 여기에 표시됩니다...")
        result_layout.addWidget(self.diff_text)
        
        layout.addWidget(result_group)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.compare_btn = QPushButton("비교 실행")
        self.compare_btn.setMinimumWidth(120)
        self.compare_btn.clicked.connect(self._compare)
        btn_layout.addWidget(self.compare_btn)
        
        self.export_btn = QPushButton("리포트 저장")
        self.export_btn.setProperty("class", "secondary")
        self.export_btn.clicked.connect(self._export_report)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)
        
        layout.addLayout(btn_layout)
        
        self._last_result = None
    
    def _select_file1(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "원본 파일 선택", "", "HWP 파일 (*.hwp *.hwpx)"
        )
        if file_path:
            self._file1_path = file_path
            self.file1_label.setText(f"✅ {Path(file_path).name}")
            self.file1_label.setStyleSheet("color: #28a745; padding: 20px;")
    
    def _select_file2(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "수정 파일 선택", "", "HWP 파일 (*.hwp *.hwpx)"
        )
        if file_path:
            self._file2_path = file_path
            self.file2_label.setText(f"✅ {Path(file_path).name}")
            self.file2_label.setStyleSheet("color: #28a745; padding: 20px;")
    
    def _compare(self) -> None:
        if not self._file1_path or not self._file2_path:
            QMessageBox.warning(self, "오류", "두 파일을 모두 선택해주세요.")
            return
        
        result = self._doc_diff.compare(self._file1_path, self._file2_path)
        self._last_result = result
        
        if not result.success:
            QMessageBox.warning(self, "오류", f"비교 실패:\n{result.error_message}")
            return
        
        # 통계 표시
        self.stats_label.setText(
            f"📊 비교 완료\n\n"
            f"원본: {result.file1_lines}줄  |  수정본: {result.file2_lines}줄\n"
            f"추가: +{result.added_count}  |  삭제: -{result.deleted_count}  |  "
            f"수정: ~{result.modified_count}\n"
            f"유사도: {result.similarity_ratio * 100:.1f}%"
        )
        
        # 변경 내역 표시
        diff_lines = []
        for change in result.changes[:50]:
            symbol = {
                ChangeType.ADDED: "+",
                ChangeType.DELETED: "-",
                ChangeType.MODIFIED: "~"
            }.get(change.change_type, " ")
            
            if change.change_type == ChangeType.ADDED:
                diff_lines.append(f"[{change.line_number:4d}] {symbol} {change.new_text}")
            elif change.change_type == ChangeType.DELETED:
                diff_lines.append(f"[{change.line_number:4d}] {symbol} {change.original_text}")
            else:
                diff_lines.append(f"[{change.line_number:4d}] {symbol} {change.original_text}")
                diff_lines.append(f"       → {change.new_text}")
        
        if len(result.changes) > 50:
            diff_lines.append(f"\n... 외 {len(result.changes) - 50}건")
        
        self.diff_text.setPlainText("\n".join(diff_lines) if diff_lines else "변경 내역 없음")
        self.export_btn.setEnabled(True)
    
    def _export_report(self) -> None:
        if not self._last_result:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "리포트 저장",
            str(Path.home() / "Documents" / "diff_report.html"),
            "HTML 파일 (*.html);;텍스트 파일 (*.txt)"
        )
        
        if file_path:
            fmt = "html" if file_path.endswith(".html") else "txt"
            if self._doc_diff.generate_report(self._last_result, file_path, fmt):
                QMessageBox.information(self, "완료", f"리포트가 저장되었습니다:\n{file_path}")
            else:
                QMessageBox.warning(self, "오류", "리포트 저장에 실패했습니다.")
