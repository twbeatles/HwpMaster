"""
Bookmark Page
북마크 관리 UI 페이지

Author: HWP Master
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QHeaderView,
    QFileDialog,
)

from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader
from ..widgets.toast import get_toast_manager
from ...utils.settings import get_settings_manager


class BookmarkPage(QWidget):
    """북마크 페이지"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.worker = None
        self._settings = get_settings_manager()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        page_header = PageHeader(
            "북마크 관리",
            "문서 내 북마크를 추출, 내보내기, 삭제합니다.",
            "🔖",
        )
        layout.addWidget(page_header)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)

        file_group = QGroupBox("문서 선택")
        file_layout = QVBoxLayout(file_group)
        self.file_list = FileListWidget()
        file_layout.addWidget(self.file_list)

        self.extract_btn = QPushButton("북마크 추출")
        self.extract_btn.clicked.connect(self._on_extract)
        file_layout.addWidget(self.extract_btn)

        main_layout.addWidget(file_group)

        bookmark_group = QGroupBox("북마크 목록")
        bookmark_layout = QVBoxLayout(bookmark_group)

        self.bookmark_table = QTableWidget()
        self.bookmark_table.setColumnCount(4)
        self.bookmark_table.setHorizontalHeaderLabels(["파일명", "이름", "페이지", "미리보기"])
        self.bookmark_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.bookmark_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bookmark_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.bookmark_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.bookmark_table.setColumnWidth(2, 60)
        bookmark_layout.addWidget(self.bookmark_table)

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

        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        layout.addStretch()

    def _run_worker(self, mode: str, files: list[str], output_dir: Optional[str] = None) -> None:
        from ...utils.worker import BookmarkWorker

        self.worker = BookmarkWorker(mode, files, output_dir)
        self.progress_card.setVisible(True)
        self.progress_card.reset()
        self.progress_card.set_title("북마크 작업")
        self.progress_card.set_status("작업 준비 중...")

        try:
            self.progress_card.cancelled.disconnect()
        except TypeError:
            pass

        self.progress_card.cancelled.connect(self.worker.cancel)
        self.worker.progress.connect(
            lambda c, t, n: (self.progress_card.set_count(c, t), self.progress_card.set_current_file(n))
        )
        self.worker.status_changed.connect(self.progress_card.set_status)
        self.worker.finished_with_result.connect(lambda res: self._on_finished(res, mode))
        self.worker.error_occurred.connect(self._on_error)

        self.worker.start()

        self.extract_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.delete_all_btn.setEnabled(False)
        self.delete_selected_btn.setEnabled(False)

    def _on_extract(self) -> None:
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return

        self.bookmark_table.setRowCount(0)
        self._run_worker("extract", files)

    def _on_export(self) -> None:
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "저장할 폴더 선택",
            self._settings.get("default_output_dir", ""),
        )
        if output_dir:
            self._run_worker("export", files, output_dir)

    def _on_delete_all(self) -> None:
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "삭제 확인",
            f"{len(files)}개 파일의 모든 북마크를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._run_worker("delete", files)

    def _on_delete_selected(self) -> None:
        get_toast_manager().info("현재 버전에서는 파일 단위 전체 삭제만 지원합니다.")

    def _populate_bookmark_table(self, bookmarks: list[tuple[str, object]]) -> None:
        self.bookmark_table.setUpdatesEnabled(False)
        self.bookmark_table.setRowCount(len(bookmarks))

        for row, (fname, bm) in enumerate(bookmarks):
            self.bookmark_table.setItem(row, 0, QTableWidgetItem(str(fname)))
            self.bookmark_table.setItem(row, 1, QTableWidgetItem(str(getattr(bm, "name", ""))))
            self.bookmark_table.setItem(row, 2, QTableWidgetItem(str(getattr(bm, "page", ""))))
            self.bookmark_table.setItem(row, 3, QTableWidgetItem(str(getattr(bm, "text_preview", ""))))

        self.bookmark_table.setUpdatesEnabled(True)

    def _on_finished(self, result, mode: str) -> None:
        self.extract_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.delete_all_btn.setEnabled(True)
        self.delete_selected_btn.setEnabled(True)

        data = getattr(result, "data", None) or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        if result.success:
            count = data.get("success_count", 0)
            fail = data.get("fail_count", 0)
            self.progress_card.set_completed(count, fail)

            if mode == "extract":
                bookmarks = data.get("bookmarks", [])
                self._populate_bookmark_table(bookmarks)
                get_toast_manager().success(f"{len(bookmarks)}개 북마크 추출 완료")
            elif mode == "export":
                get_toast_manager().success(f"{count}개 파일 내보내기 완료")
            elif mode == "delete":
                get_toast_manager().success(f"{count}개 파일에서 북마크 삭제 완료")
                if count > 0:
                    self._on_extract()
        else:
            self.progress_card.set_error(getattr(result, "error_message", None) or "오류 발생")
            get_toast_manager().error(f"오류: {result.error_message}")

    def _on_error(self, message: str) -> None:
        self.progress_card.set_error(message)
        get_toast_manager().error(f"작업 중 오류 발생: {message}")
