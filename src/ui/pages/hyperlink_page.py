"""
Hyperlink Page
하이퍼링크 검사 UI 페이지

Author: HWP Master
"""

from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QHeaderView,
    QFileDialog,
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ..widgets.file_list import FileListWidget
from ..widgets.page_header import PageHeader
from ..widgets.toast import get_toast_manager
from ...utils.settings import get_settings_manager
from ...core.hyperlink_checker import HyperlinkChecker


class HyperlinkPage(QWidget):
    """하이퍼링크 검사 페이지"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.temp_dir: str = ""
        self.worker = None
        self._settings = get_settings_manager()
        self._links: list[tuple[str, object]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        page_header = PageHeader(
            "하이퍼링크 검사",
            "문서 내 링크를 추출하고 유효성을 검사합니다.",
            "🔗",
        )
        layout.addWidget(page_header)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)

        file_group = QGroupBox("문서 선택")
        file_layout = QVBoxLayout(file_group)
        self.file_list = FileListWidget()
        file_layout.addWidget(self.file_list)

        self.scan_btn = QPushButton("링크 검사 시작")
        self.scan_btn.clicked.connect(self._on_scan)
        file_layout.addWidget(self.scan_btn)

        main_layout.addWidget(file_group)

        result_group = QGroupBox("검사 결과")
        result_layout = QVBoxLayout(result_group)

        stats_layout = QHBoxLayout()
        self.total_label = QLabel("총 링크: 0개")
        self.valid_label = QLabel("유효: 0개")
        self.valid_label.setStyleSheet("color: #3fb950;")
        self.broken_label = QLabel("오류: 0개")
        self.broken_label.setStyleSheet("color: #f85149;")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.valid_label)
        stats_layout.addWidget(self.broken_label)
        stats_layout.addStretch()
        result_layout.addLayout(stats_layout)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        result_layout.addWidget(self.progress)

        self.link_table = QTableWidget()
        self.link_table.setColumnCount(4)
        self.link_table.setHorizontalHeaderLabels(["상태", "URL", "텍스트", "오류"])
        self.link_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.link_table.setColumnWidth(0, 50)
        self.link_table.setColumnWidth(2, 150)
        self.link_table.setColumnWidth(3, 150)
        result_layout.addWidget(self.link_table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.export_btn = QPushButton("리포트 저장")
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)

        result_layout.addLayout(btn_layout)
        main_layout.addWidget(result_group, 1)

        layout.addLayout(main_layout)

    def _on_scan(self) -> None:
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return

        external_enabled = bool(self._settings.get("hyperlink_external_requests_enabled", True))
        notice_shown = bool(self._settings.get("hyperlink_privacy_notice_shown", False))
        if external_enabled and not notice_shown:
            reply = QMessageBox.warning(
                self,
                "외부 접속 안내",
                "하이퍼링크 검사는 문서의 외부 URL에 실제 접속할 수 있습니다.\n"
                "보안/개인정보 정책에 따라 제한이 필요할 수 있습니다.\n\n"
                "계속 진행하시겠습니까?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.No:
                external_enabled = False
                self._settings.set("hyperlink_external_requests_enabled", False)
            self._settings.set("hyperlink_privacy_notice_shown", True)

        self.link_table.setRowCount(0)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.scan_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        from ...utils.worker import HyperlinkWorker
        import tempfile

        self.temp_dir = tempfile.mkdtemp()
        timeout_sec = int(self._settings.get("hyperlink_timeout_sec", 5))
        allowlist = str(self._settings.get("hyperlink_domain_allowlist", ""))

        self.worker = HyperlinkWorker(
            files,
            self.temp_dir,
            external_requests_enabled=external_enabled,
            timeout_sec=timeout_sec,
            domain_allowlist=allowlist,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_with_result.connect(self._on_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self.progress.setValue(int(current / total * 100))
        self.total_label.setText(f"검사 중: {message}")

    def _populate_link_table(self, links: list[tuple[str, object]]) -> None:
        self.link_table.setUpdatesEnabled(False)
        self.link_table.setRowCount(len(links))

        for row, (_, link) in enumerate(links):
            ok = getattr(link.status, "value", "") in ["valid", "local_ok"]
            status_text = "✅" if ok else "❌"
            status_color = "#3fb950" if ok else "#f85149"

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.link_table.setItem(row, 0, status_item)
            self.link_table.setItem(row, 1, QTableWidgetItem(getattr(link, "url", "")))
            self.link_table.setItem(row, 2, QTableWidgetItem(getattr(link, "text", "")))
            self.link_table.setItem(row, 3, QTableWidgetItem(getattr(link, "error_message", "")))

        self.link_table.setUpdatesEnabled(True)

    def _on_finished(self, result) -> None:
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

        if result.success:
            links = (result.data or {}).get("links", [])
            self._links = links

            total = len(links)
            valid = sum(1 for _, l in links if getattr(l.status, "value", "") in ["valid", "local_ok"])
            broken = sum(
                1
                for _, l in links
                if getattr(l.status, "value", "") in ["broken", "local_missing", "timeout"]
            )

            self.total_label.setText(f"총 링크: {total}개")
            self.valid_label.setText(f"유효: {valid}개")
            self.broken_label.setText(f"오류: {broken}개")

            self._populate_link_table(links)
            get_toast_manager().success("링크 검사 완료")
        else:
            get_toast_manager().error(f"오류: {result.error_message}")

    def _on_error(self, message: str) -> None:
        get_toast_manager().error(f"작업 중 오류 발생: {message}")

    def _on_export(self) -> None:
        if self.link_table.rowCount() == 0:
            get_toast_manager().warning("검사 결과가 없습니다.")
            return

        default_dir = self._settings.get("default_output_dir", "")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "리포트 저장",
            str(Path(default_dir) / "hyperlink_report.xlsx") if default_dir else "",
            "Excel 파일 (*.xlsx);;HTML 파일 (*.html)",
        )
        if not file_path:
            return

        try:
            import html

            if file_path.lower().endswith(".xlsx"):
                checker = HyperlinkChecker()
                ok = checker.export_links_to_excel(self._links, file_path)
                if not ok:
                    raise RuntimeError("엑셀 저장 실패")
                get_toast_manager().success(f"엑셀 저장 완료: {file_path}")
                return

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("<html><head><meta charset='utf-8'><style>")
                f.write("table { border-collapse: collapse; width: 100%; }")
                f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
                f.write(".valid { color: green; } .broken { color: red; }")
                f.write("</style></head><body>")
                f.write(f"<h1>링크 검사 결과 ({html.escape(self.total_label.text())})</h1>")
                f.write("<table><tr><th>상태</th><th>URL</th><th>텍스트</th><th>오류</th></tr>")

                for r in range(self.link_table.rowCount()):
                    status_item = self.link_table.item(r, 0)
                    url_item = self.link_table.item(r, 1)
                    text_item = self.link_table.item(r, 2)
                    error_item = self.link_table.item(r, 3)

                    status = status_item.text() if status_item else ""
                    url = url_item.text() if url_item else ""
                    text = text_item.text() if text_item else ""
                    error = error_item.text() if error_item else ""
                    cls = "valid" if status == "✅" else "broken"
                    f.write(
                        f"<tr><td class='{cls}'>{html.escape(status)}</td>"
                        f"<td>{html.escape(url)}</td>"
                        f"<td>{html.escape(text)}</td>"
                        f"<td>{html.escape(error)}</td></tr>"
                    )

                f.write("</table></body></html>")

            get_toast_manager().success(f"리포트 저장 완료: {file_path}")
        except Exception as e:
            get_toast_manager().error(f"저장 실패: {e}")
