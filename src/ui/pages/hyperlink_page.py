"""
Hyperlink Page
하이퍼링크 검사 UI 페이지

Author: HWP Master
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QFileDialog, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ..widgets.file_list import FileListWidget
from ..widgets.toast import get_toast_manager


class HyperlinkPage(QWidget):
    """하이퍼링크 검사 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.temp_dir: str = ""
        self.worker = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # 헤더
        header = QLabel("🔗 하이퍼링크 검사")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(header)
        
        desc = QLabel("문서 내 링크를 추출하고 유효성을 검사합니다.")
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
        
        self.scan_btn = QPushButton("링크 검사 시작")
        self.scan_btn.clicked.connect(self._on_scan)
        file_layout.addWidget(self.scan_btn)
        
        main_layout.addWidget(file_group)
        
        # 검사 결과
        result_group = QGroupBox("검사 결과")
        result_layout = QVBoxLayout(result_group)
        
        # 통계
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
        
        # 진행률
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        result_layout.addWidget(self.progress)
        
        # 테이블
        self.link_table = QTableWidget()
        self.link_table.setColumnCount(4)
        self.link_table.setHorizontalHeaderLabels(["상태", "URL", "텍스트", "오류"])
        self.link_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.link_table.setColumnWidth(0, 50)
        self.link_table.setColumnWidth(2, 150)
        self.link_table.setColumnWidth(3, 150)
        result_layout.addWidget(self.link_table)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.export_btn = QPushButton("리포트 저장")
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)
        
        result_layout.addLayout(btn_layout)
        main_layout.addWidget(result_group, 1)
        
        layout.addLayout(main_layout)
    
    
    def _on_scan(self) -> None:
        """링크 검사 시작"""
        files = self.file_list.get_files()
        if not files:
            get_toast_manager().warning("파일을 추가해주세요.")
            return
        
        self.link_table.setRowCount(0)
        self.progress.setVisible(True)
        self.scan_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        
        from ...utils.worker import HyperlinkWorker
        # 리포트 저장을 위한 임시 폴더 혹은 사용자 선택?
        # 예제에서는 검사 후 내보내기를 따로 하므로, 검사 단계에서는 report 생성을 안 하거나 임시 폴더 사용
        # 여기서는 report 생성 없이 검사만 수행 (Worker 수정 필요할 수도 있음, output_dir 필수인지 확인)
        # Worker: __init__(files, output_dir)
        # output_dir이 필수라면 임시 폴더 사용
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        
        self.worker = HyperlinkWorker(files, self.temp_dir)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_with_result.connect(self._on_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress.setValue(int(current / total * 100))
        self.total_label.setText(f"검사 중: {message}")
        
    def _on_finished(self, result) -> None:
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        
        if result.success:
            links = result.data.get("links", [])
            valid_count = result.data.get("success_count", 0) # 문서 성공 개수가 아니라 링크 성공 개수? 
            # Worker에서 success_count는 성공한 *파일* 수, total_links는 *링크* 수
            # Data: success_count, total_links, links
            
            # 링크 데이터를 기반으로 카운트 다시 계산
            total = len(links)
            valid = sum(1 for _, l in links if l.status.value in ["valid", "local_ok"])
            broken = total - valid
            
            self.total_label.setText(f"총 링크: {total}개")
            self.valid_label.setText(f"유효: {valid}개")
            self.broken_label.setText(f"오류: {broken}개")
            
            # 테이블 채우기
            self.link_table.setRowCount(0)
            for fname, link in links:
                row = self.link_table.rowCount()
                self.link_table.insertRow(row)
                
                status_text = "✓" if link.status.value in ["valid", "local_ok"] else "✗"
                status_color = "#3fb950" if link.status.value in ["valid", "local_ok"] else "#f85149"
                
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor(status_color))
                self.link_table.setItem(row, 0, status_item)
                self.link_table.setItem(row, 1, QTableWidgetItem(link.url))
                self.link_table.setItem(row, 2, QTableWidgetItem(link.text))
                self.link_table.setItem(row, 3, QTableWidgetItem(link.error_message))
            
            get_toast_manager().success("링크 검사 완료")
        else:
            get_toast_manager().error(f"오류: {result.error_message}")

    def _on_error(self, message: str) -> None:
        get_toast_manager().error(f"작업 중 오류 발생: {message}")

    
    def _on_export(self) -> None:
        """리포트 저장 (HTML)"""
        # 현재 테이블 내용을 기반으로 리포트 생성 또는 Worker가 생성한 리포트 활용?
        # Worker는 개별 파일 리포트를 생성함. 
        # 여기서는 "통합 리포트"를 원하는지, 개별 리포트를 원하는지?
        # mock code는 saveFileName으로 하나의 파일을 요구함.
        # 통합 리포트를 생성해서 저장하는 것이 좋음.
        
        if self.link_table.rowCount() == 0:
            get_toast_manager().warning("검사 결과가 없습니다.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "리포트 저장", "", "HTML 파일 (*.html)"
        )
        if file_path:
            try:
                # 간단한 통합 리포트 생성
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("<html><head><meta charset='utf-8'><style>")
                    f.write("table { border-collapse: collapse; width: 100%; }")
                    f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
                    f.write(".valid { color: green; } .broken { color: red; }")
                    f.write("</style></head><body>")
                    f.write(f"<h1>링크 검사 결과 ({self.total_label.text()})</h1>")
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
                        cls = "valid" if status == "✓" else "broken"
                        f.write(f"<tr><td class='{cls}'>{status}</td><td>{url}</td><td>{text}</td><td>{error}</td></tr>")
                    
                    f.write("</table></body></html>")
                
                get_toast_manager().success(f"리포트 저장 완료: {file_path}")
            except Exception as e:
                get_toast_manager().error(f"저장 실패: {e}")

