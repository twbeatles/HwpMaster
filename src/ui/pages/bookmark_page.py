"""
Bookmark Page
북마크 관리 UI 페이지

Author: HWP Master
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt

from ..widgets.file_list import FileListWidget
from ..widgets.toast import get_toast_manager


class BookmarkPage(QWidget):
    """북마크 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.worker = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # 헤더
        header = QLabel("🔖 북마크 관리")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(header)
        
        desc = QLabel("문서 내 북마크를 추출, 편집, 삭제합니다.")
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
        
        self.extract_btn = QPushButton("북마크 추출")
        self.extract_btn.clicked.connect(self._on_extract)
        file_layout.addWidget(self.extract_btn)
        
        main_layout.addWidget(file_group)
        
        # 북마크 목록
        bookmark_group = QGroupBox("북마크 목록")
        bookmark_layout = QVBoxLayout(bookmark_group)
        
        self.bookmark_table = QTableWidget()
        # 북마크 목록 테이블 컬럼 확장 (파일명 포함)
        self.bookmark_table.setColumnCount(4)
        self.bookmark_table.setHorizontalHeaderLabels(["파일명", "이름", "페이지", "미리보기"])
        self.bookmark_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.bookmark_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bookmark_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.bookmark_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.bookmark_table.setColumnWidth(2, 60)
        
        # 버튼들
        table_btn_layout = QHBoxLayout()
        
        self.delete_selected_btn = QPushButton("선택 삭제")
        self.delete_selected_btn.setProperty("class", "secondary")
        self.delete_selected_btn.clicked.connect(self._on_delete_selected)
        table_btn_layout.addWidget(self.delete_selected_btn)
        
        self.delete_all_btn = QPushButton("전체 삭제")
        self.delete_all_btn.setProperty("class", "secondary")
        self.delete_all_btn.clicked.connect(self._on_delete_all)
        table_btn_layout.addWidget(self.delete_all_btn)
        
        table_btn_layout.addStretch()
        
        self.export_btn = QPushButton("Excel 내보내기")
        self.export_btn.clicked.connect(self._on_export)
        table_btn_layout.addWidget(self.export_btn)
        
        bookmark_layout.addLayout(table_btn_layout)
        main_layout.addWidget(bookmark_group, 1)
        
        layout.addLayout(main_layout)
        layout.addStretch()
    
    def _run_worker(self, mode: str, files: list[str], output_dir: Optional[str] = None) -> None:
        """작업 실행 공통 메서드"""
        from ...utils.worker import BookmarkWorker
        
        self.worker = BookmarkWorker(mode, files, output_dir)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_with_result.connect(lambda res: self._on_finished(res, mode))
        self.worker.error_occurred.connect(self._on_error)
        
        self.worker.start()
        
        # UI 잠금
        self.extract_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.delete_all_btn.setEnabled(False)
        self.delete_selected_btn.setEnabled(False)
        
    def _on_extract(self) -> None:
        """북마크 추출"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
        
        self.bookmark_table.setRowCount(0)
        self._run_worker("extract", files)
        
    def _on_export(self) -> None:
        """Excel 내보내기"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return

        # 폴더 선택으로 변경 (Batch Export)
        output_dir = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택")
        if output_dir:
            self._run_worker("export", files, output_dir)
            
    def _on_delete_all(self) -> None:
        """전체 삭제"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
            
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "삭제 확인", 
            f"{len(files)}개 파일의 모든 북마크를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._run_worker("delete", files)

    def _on_delete_selected(self) -> None:
        """선택 삭제 (구현 복잡성으로 인해 현재는 파일 단위 전체 삭제 경고)"""
        # 개별 북마크 삭제는 현재 구조(Batch) 상 UI 매핑이 필요함.
        # 일단은 Toast로 안내
        get_toast_manager().info("현재 버전에서는 파일 단위 전체 삭제만 지원합니다.")

    def _on_progress(self, current: int, total: int, message: str) -> None:
        get_toast_manager().info(f"처리 중: {message} ({current}/{total})")
    
    def _on_finished(self, result, mode: str) -> None:
        self.extract_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.delete_all_btn.setEnabled(True)
        self.delete_selected_btn.setEnabled(True)
        
        if result.success:
            count = result.data.get("success_count", 0)
            
            if mode == "extract":
                bookmarks = result.data.get("bookmarks", [])
                self.bookmark_table.setRowCount(0)
                
                for fname, bm in bookmarks:
                    row = self.bookmark_table.rowCount()
                    self.bookmark_table.insertRow(row)
                    self.bookmark_table.setItem(row, 0, QTableWidgetItem(fname))
                    self.bookmark_table.setItem(row, 1, QTableWidgetItem(bm.name))
                    self.bookmark_table.setItem(row, 2, QTableWidgetItem(str(bm.page)))
                    self.bookmark_table.setItem(row, 3, QTableWidgetItem(bm.text_preview))
                
                get_toast_manager().success(f"{len(bookmarks)}개 북마크 추출 완료")
                
            elif mode == "export":
                get_toast_manager().success(f"{count}개 파일 내보내기 완료")
                
            elif mode == "delete":
                get_toast_manager().success(f"{count}개 파일에서 북마크 삭제 완료")
                if count > 0:
                    self._on_extract() # 목록 갱신
        else:
            get_toast_manager().error(f"오류: {result.error_message}")
            
    def _on_error(self, message: str) -> None:
        get_toast_manager().error(f"작업 중 오류 발생: {message}")

