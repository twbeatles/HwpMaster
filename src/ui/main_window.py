"""
Main Window Module
PySide6 기반 메인 윈도우 UI

Author: HWP Master
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QSizePolicy, QSpacerItem, QFileDialog, QMessageBox,
    QScrollArea
)
from PySide6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve,
    Signal, Slot, QParallelAnimationGroup
)
from PySide6.QtGui import QIcon, QFont, QColor

from .widgets.file_list import FileListWidget
from .widgets.progress_card import ProgressCard
from .widgets.sidebar_button import SidebarButton
from .widgets.feature_card import FeatureCard
from .widgets.toast import ToastManager, ToastType, get_toast_manager
from ..utils.worker import ConversionWorker, MergeWorker, SplitWorker, DataInjectWorker, MetadataCleanWorker, WorkerResult
from ..utils.settings import get_settings_manager





class Sidebar(QFrame):
    """사이드바 네비게이션"""
    
    page_changed = Signal(int)
    
    # 네비게이션 아이템 정의 (섹션별)
    NAV_SECTIONS = [
        ("기본", [
            ("🏠", "홈"),
            ("🔄", "변환"),
            ("📎", "병합/분할"),
            ("📝", "데이터 주입"),
            ("🧹", "메타정보 정리"),
        ]),
        ("고급", [
            ("📦", "템플릿 스토어"),
            ("🎬", "매크로 레코더"),
            ("🔤", "정규식 치환"),
        ]),
        ("분석", [
            ("👮", "서식 도우미"),
            ("🩺", "표 도우미"),
            ("📊", "문서 비교"),
            ("📑", "자동 목차"),
        ]),
        ("생산성", [
            ("💧", "워터마크"),
            ("📄", "헤더/푸터"),
            ("🔖", "북마크"),
            ("🔗", "링크 검사"),
            ("🖼️", "이미지 추출"),
        ]),
        ("", [
            ("⚙️", "설정"),
        ]),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(280)
        
        self._is_collapsed = False
        self._buttons: list[SidebarButton] = []
        self._nav_items: list[tuple[str, str]] = []
        
        # 메인 레이아웃 (여백 없음)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. 헤더 영역 (로고, 타이틀) - 고정
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 20, 12, 16)
        header_layout.setSpacing(2)
        
        # 로고 컨테이너
        logo_container = QWidget()
        logo_container.setStyleSheet("background: transparent;")
        logo_inner = QHBoxLayout(logo_container)
        logo_inner.setContentsMargins(8, 0, 8, 0)
        logo_inner.setSpacing(12)
        
        logo_icon = QLabel("📄")
        logo_icon.setStyleSheet("font-size: 28px; background: transparent;")
        logo_inner.addWidget(logo_icon)
        
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_inner = QVBoxLayout(title_container)
        title_inner.setContentsMargins(0, 0, 0, 0)
        title_inner.setSpacing(0)
        
        self._title_label = QLabel("HWP Master")
        self._title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #ffffff; background: transparent;")
        title_inner.addWidget(self._title_label)
        
        self._version_label = QLabel("v5.0")
        self._version_label.setStyleSheet("color: #8957e5; font-size: 11px; background: transparent;")
        title_inner.addWidget(self._version_label)
        
        logo_inner.addWidget(title_container)
        logo_inner.addStretch()
        header_layout.addWidget(logo_container)
        header_layout.addSpacing(20)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #30363d;")
        header_layout.addWidget(line)
        
        main_layout.addWidget(header_widget)
        
        # 2. 스크롤 영역 (메뉴 버튼들)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 0px; background: transparent; }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(12, 10, 12, 10)
        self._scroll_layout.setSpacing(4)
        
        # 섹션별 네비게이션 버튼들
        btn_index = 0
        for section_name, items in self.NAV_SECTIONS:
            if section_name:
                section_label = QLabel(section_name)
                section_label.setStyleSheet("""
                    color: #484f58;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    padding: 12px 10px 6px 10px;
                    background: transparent;
                """)
                self._scroll_layout.addWidget(section_label)
            
            for icon, text in items:
                self._nav_items.append((icon, text))
                btn = SidebarButton(f"  {icon}  {text}")
                btn.clicked.connect(lambda checked, i=btn_index: self._on_button_clicked(i))
                self._buttons.append(btn)
                self._scroll_layout.addWidget(btn)
                btn_index += 1
        
        # 첫 번째 버튼 선택
        if self._buttons:
            self._buttons[0].setChecked(True)
            
        self._scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 3. 하단 토글 버튼 영역 - 고정
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(12, 10, 12, 16)
        
        self._toggle_btn = QPushButton("◀  메뉴 접기")
        self._toggle_btn.setMinimumHeight(32)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #8b949e;
                font-size: 12px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background: rgba(139, 148, 158, 0.1);
                color: #e6edf3;
            }
        """)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        footer_layout.addWidget(self._toggle_btn)
        
        main_layout.addWidget(footer_widget)
    
    def _on_button_clicked(self, index: int) -> None:
        """버튼 클릭 처리"""
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)
    
    def _toggle_collapse(self) -> None:
        """사이드바 접기/펼치기"""
        self._is_collapsed = not self._is_collapsed
        
        target_width = 70 if self._is_collapsed else 280
        
        animation = QPropertyAnimation(self, b"minimumWidth")
        animation.setDuration(200)
        animation.setEndValue(target_width)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        animation2 = QPropertyAnimation(self, b"maximumWidth")
        animation2.setDuration(200)
        animation2.setEndValue(target_width)
        animation2.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        group = QParallelAnimationGroup(self)
        group.addAnimation(animation)
        group.addAnimation(animation2)
        group.start()
        
        if self._is_collapsed:
            self._toggle_btn.setText("▶")
            self._toggle_btn.setStyleSheet(self._toggle_btn.styleSheet() + "text-align: center; padding-left: 0px;")
        else:
            self._toggle_btn.setText("◀  메뉴 접기")
            self._toggle_btn.setStyleSheet(self._toggle_btn.styleSheet().replace("text-align: center; padding-left: 0px;", "text-align: left; padding-left: 10px;"))
        
        # 로고 및 버전 토글
        self._title_label.setVisible(not self._is_collapsed)
        self._version_label.setVisible(not self._is_collapsed)
        
        # 버튼 텍스트 토글
        for btn, (icon, text) in zip(self._buttons, self._nav_items):
            if self._is_collapsed:
                btn.setText(f"  {icon}")
            else:
                btn.setText(f"  {icon}  {text}")



from .pages import (
    HomePage, ConvertPage, MergeSplitPage, DataInjectPage, 
    MetadataPage, SettingsPage
)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings_manager()
        
        self.setWindowTitle("HWP Master")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 사이드바
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self.sidebar)
        
        # 페이지 스택
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)
        
        # 페이지들 추가
        self.home_page = HomePage()
        self.home_page.card_clicked.connect(self._on_page_changed)
        
        self.convert_page = ConvertPage()
        self.merge_split_page = MergeSplitPage()
        self.data_inject_page = DataInjectPage()
        self.metadata_page = MetadataPage()
        self.settings_page = SettingsPage()
        self._sync_settings_page()
        
        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.convert_page)
        self.page_stack.addWidget(self.merge_split_page)
        self.page_stack.addWidget(self.data_inject_page)
        self.page_stack.addWidget(self.metadata_page)
        
        # Phase 2 페이지들
        from .pages.template_page import TemplatePage
        from .pages.macro_page import MacroPage
        from .pages.regex_page import RegexPage
        
        self.template_page = TemplatePage()
        self.macro_page = MacroPage()
        self.regex_page = RegexPage()
        
        self.page_stack.addWidget(self.template_page)
        self.page_stack.addWidget(self.macro_page)
        self.page_stack.addWidget(self.regex_page)
        
        # Phase 3-4 페이지들
        from .pages.style_cop_page import StyleCopPage
        from .pages.table_doctor_page import TableDoctorPage
        from .pages.doc_diff_page import DocDiffPage
        from .pages.smart_toc_page import SmartTocPage
        
        self.style_cop_page = StyleCopPage()
        self.table_doctor_page = TableDoctorPage()
        self.doc_diff_page = DocDiffPage()
        self.smart_toc_page = SmartTocPage()
        
        self.page_stack.addWidget(self.style_cop_page)
        self.page_stack.addWidget(self.table_doctor_page)
        self.page_stack.addWidget(self.doc_diff_page)
        self.page_stack.addWidget(self.smart_toc_page)
        
        # Phase 5 페이지들
        from .pages.watermark_page import WatermarkPage
        from .pages.header_footer_page import HeaderFooterPage
        from .pages.bookmark_page import BookmarkPage
        from .pages.hyperlink_page import HyperlinkPage
        from .pages.image_extractor_page import ImageExtractorPage
        
        self.watermark_page = WatermarkPage()
        self.header_footer_page = HeaderFooterPage()
        self.bookmark_page = BookmarkPage()
        self.hyperlink_page = HyperlinkPage()
        self.image_extractor_page = ImageExtractorPage()
        
        self.page_stack.addWidget(self.watermark_page)
        self.page_stack.addWidget(self.header_footer_page)
        self.page_stack.addWidget(self.bookmark_page)
        self.page_stack.addWidget(self.hyperlink_page)
        self.page_stack.addWidget(self.image_extractor_page)
        
        self.page_stack.addWidget(self.settings_page)
        
        # 시그널 연결
        self._connect_signals()
        
        # Worker 참조
        self._current_worker = None

    def _get_default_output_dir(self) -> str:
        """설정 기반 기본 출력 디렉토리 반환"""
        configured = self._settings.get("default_output_dir", "")
        if configured and Path(configured).exists():
            return configured
        return str(Path.home() / "Documents")

    def _sync_settings_page(self) -> None:
        """설정값을 설정 페이지 UI에 반영"""
        default_output_dir = self._settings.get("default_output_dir", "")
        if default_output_dir:
            self.settings_page.output_label.setText(default_output_dir)
    
    def set_busy(self, busy: bool) -> None:
        """작업 중 상태 설정"""
        self.sidebar.setEnabled(not busy)
        
        # 커서 변경
        if busy:
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.unsetCursor()

    def _connect_signals(self) -> None:
        """시그널 연결"""
        # 변환 페이지
        self.convert_page.convert_btn.clicked.connect(self._on_convert)
        
        # 병합/분할 페이지
        self.merge_split_page.execute_btn.clicked.connect(self._on_merge_split)
        
        # 데이터 주입 페이지
        self.data_inject_page.template_btn.clicked.connect(self._select_template)
        self.data_inject_page.data_btn.clicked.connect(self._select_data_file)
        self.data_inject_page.execute_btn.clicked.connect(self._on_inject)
        
        # 메타데이터 페이지
        self.metadata_page.execute_btn.clicked.connect(self._on_clean_metadata)
        
        # 설정 페이지
        self.settings_page.output_btn.clicked.connect(self._select_output_dir)
    
    @Slot(int)
    def _on_page_changed(self, index: int) -> None:
        """페이지 변경"""
        self.page_stack.setCurrentIndex(index)
    
    @Slot()
    def _on_convert(self) -> None:
        """변환 실행"""
        files = self.convert_page.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "알림", "변환할 파일을 추가해주세요.")
            return
        
        # 선택된 포맷 가져오기
        target_format = "PDF"
        for btn in self.convert_page.format_buttons:
            if btn.isChecked():
                target_format = btn.text()
                break
        
        self.convert_page.progress_card.setVisible(True)
        self.convert_page.progress_card.set_status("변환 준비 중...")
        self.convert_page.convert_btn.setEnabled(False)
        
        # Worker 시작
        self.set_busy(True)
        self._current_worker = ConversionWorker(files, target_format)
        self._current_worker.progress.connect(
            lambda c, t, n: self.convert_page.progress_card.set_count(c, t)
        )
        self._current_worker.status_changed.connect(
            lambda s: self.convert_page.progress_card.set_status(s)
        )
        self._current_worker.finished_with_result.connect(self._on_convert_finished)
        self._current_worker.start()
    
    @Slot(object)
    def _on_convert_finished(self, result: WorkerResult) -> None:
        """변환 완료 콜백"""
        self.set_busy(False)
        self.convert_page.convert_btn.setEnabled(True)
        
        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.convert_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self, "완료",
                f"변환이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개"
            )
        else:
            self.convert_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "변환 중 오류가 발생했습니다.")
    
    @Slot()
    def _on_merge_split(self) -> None:
        """병합/분할 실행"""
        files = self.merge_split_page.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "알림", "파일을 추가해주세요.")
            return
        
        # 병합 모드 확인
        is_merge = self.merge_split_page.merge_btn.isChecked()
        
        self.merge_split_page.progress_card.setVisible(True)
        self.merge_split_page.progress_card.set_status("처리 준비 중...")
        self.merge_split_page.execute_btn.setEnabled(False)
        
        if is_merge:
            # 병합 출력 파일 선택
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "병합 파일 저장",
                str(Path(self._get_default_output_dir()) / "merged.hwp"),
                "HWP 파일 (*.hwp)"
            )
            if not output_path:
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return
            
            self.set_busy(True)
            self._current_worker = MergeWorker(files, output_path)
            self._current_worker.progress.connect(
                lambda c, t, n: self.merge_split_page.progress_card.set_count(c, t)
            )
            self._current_worker.finished_with_result.connect(self._on_merge_finished)
            self._current_worker.start()
        else:
            # 분할 모드
            files = self.merge_split_page.file_list.get_files()
            if not files:
                QMessageBox.warning(self, "알림", "분할할 파일을 추가해주세요.")
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return
            
            if len(files) > 1:
                QMessageBox.warning(self, "알림", "분할은 한 번에 하나의 파일만 처리할 수 있습니다.")
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return
            
            page_ranges = self.merge_split_page.get_page_ranges()
            if not page_ranges:
                QMessageBox.warning(self, "알림", "페이지 범위를 입력해주세요.\n예: 1-3, 4-6")
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return
            
            # 출력 디렉토리 선택
            output_dir = QFileDialog.getExistingDirectory(
                self, "분할 파일 저장 위치", self._get_default_output_dir()
            )
            if not output_dir:
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return
            
            self.set_busy(True)
            self._current_worker = SplitWorker(files[0], page_ranges, output_dir)
            self._current_worker.progress.connect(
                lambda c, t, n: self.merge_split_page.progress_card.set_count(c, t)
            )
            self._current_worker.status_changed.connect(
                lambda s: self.merge_split_page.progress_card.set_status(s)
            )
            self._current_worker.finished_with_result.connect(self._on_split_finished)
            self._current_worker.start()
    
    @Slot(object)
    def _on_merge_finished(self, result: WorkerResult) -> None:
        """병합 완료 콜백"""
        self.set_busy(False)
        self.merge_split_page.execute_btn.setEnabled(True)
        
        if result.success:
            self.merge_split_page.progress_card.set_completed(1, 0)
            QMessageBox.information(self, "완료", "파일 병합이 완료되었습니다.")
        else:
            self.merge_split_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "병합 중 오류가 발생했습니다.")
    
    @Slot(object)
    def _on_split_finished(self, result: WorkerResult) -> None:
        """분할 완료 콜백"""
        self.set_busy(False)
        self.merge_split_page.execute_btn.setEnabled(True)
        
        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.merge_split_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self, "완료",
                f"파일 분할이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개"
            )
        else:
            self.merge_split_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "분할 중 오류가 발생했습니다.")
    
    @Slot()
    def _select_template(self) -> None:
        """템플릿 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "템플릿 파일 선택",
            "",
            "HWP 파일 (*.hwp *.hwpx)"
        )
        if file_path:
            self.data_inject_page.template_label.setText(file_path)
            self.data_inject_page.template_label.setStyleSheet("color: #e8e8e8;")
    
    @Slot()
    def _select_data_file(self) -> None:
        """데이터 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "데이터 파일 선택",
            "",
            "Excel 파일 (*.xlsx *.xls);;CSV 파일 (*.csv)"
        )
        if file_path:
            self.data_inject_page.data_label.setText(file_path)
            self.data_inject_page.data_label.setStyleSheet("color: #e8e8e8;")
    
    @Slot()
    def _on_inject(self) -> None:
        """데이터 주입 실행"""
        template = self.data_inject_page.template_label.text()
        data_file = self.data_inject_page.data_label.text()
        
        if "선택된 파일 없음" in template:
            QMessageBox.warning(self, "알림", "템플릿 파일을 선택해주세요.")
            return
        
        if "선택된 파일 없음" in data_file:
            QMessageBox.warning(self, "알림", "데이터 파일을 선택해주세요.")
            return
        
        # 출력 디렉토리 선택
        output_dir = QFileDialog.getExistingDirectory(
            self, "출력 폴더 선택", self._get_default_output_dir()
        )
        if not output_dir:
            return

        data_rows: list[dict[str, str]] = []
        
        # 데이터 파일 읽기
        try:
            from ..core.excel_handler import ExcelHandler
            handler = ExcelHandler()
            
            if data_file.endswith('.csv'):
                read_result = handler.read_csv(data_file)
            else:
                read_result = handler.read_excel(data_file)

            if not read_result.success:
                QMessageBox.warning(self, "오류", read_result.error_message or "데이터 파일 읽기에 실패했습니다.")
                return

            if not read_result.data:
                QMessageBox.warning(self, "알림", "데이터 파일이 비어있습니다.")
                return

            for row in read_result.data:
                normalized_row = {
                    str(key): "" if value is None else str(value)
                    for key, value in row.items()
                }
                data_rows.append(normalized_row)
                
        except Exception as e:
            QMessageBox.warning(self, "오류", f"데이터 파일 읽기 실패:\n{e}")
            return
        
        self.data_inject_page.progress_card.setVisible(True)
        self.data_inject_page.progress_card.set_status("문서 생성 중...")
        self.data_inject_page.execute_btn.setEnabled(False)
        
        # Worker 시작
        self.set_busy(True)
        self._current_worker = DataInjectWorker(
            template, data_rows, output_dir
        )
        self._current_worker.progress.connect(
            lambda c, t, n: self.data_inject_page.progress_card.set_count(c, t)
        )
        self._current_worker.status_changed.connect(
            lambda s: self.data_inject_page.progress_card.set_status(s)
        )
        self._current_worker.finished_with_result.connect(self._on_inject_finished)
        self._current_worker.start()
    
    @Slot(object)
    def _on_inject_finished(self, result: WorkerResult) -> None:
        """데이터 주입 완료 콜백"""
        self.set_busy(False)
        self.data_inject_page.execute_btn.setEnabled(True)
        
        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.data_inject_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self, "완료",
                f"데이터 주입이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개"
            )
        else:
            self.data_inject_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "데이터 주입 중 오류가 발생했습니다.")
    
    @Slot()
    def _on_clean_metadata(self) -> None:
        """메타데이터 정리 실행"""
        files = self.metadata_page.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "알림", "파일을 추가해주세요.")
            return
        
        self.metadata_page.progress_card.setVisible(True)
        self.metadata_page.progress_card.set_status("메타정보 정리 중...")
        self.metadata_page.execute_btn.setEnabled(False)
        
        # Worker 시작
        self.set_busy(True)
        self._current_worker = MetadataCleanWorker(files)
        self._current_worker.progress.connect(
            lambda c, t, n: self.metadata_page.progress_card.set_count(c, t)
        )
        self._current_worker.status_changed.connect(
            lambda s: self.metadata_page.progress_card.set_status(s)
        )
        self._current_worker.finished_with_result.connect(self._on_metadata_finished)
        self._current_worker.start()
    
    @Slot(object)
    def _on_metadata_finished(self, result: WorkerResult) -> None:
        """메타데이터 정리 완료 콜백"""
        self.set_busy(False)
        self.metadata_page.execute_btn.setEnabled(True)
        
        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.metadata_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self, "완료",
                f"메타정보 정리가 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개"
            )
        else:
            self.metadata_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "메타정보 정리 중 오류가 발생했습니다.")    
    @Slot()
    def _select_output_dir(self) -> None:
        """출력 디렉토리 선택"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "출력 폴더 선택",
            self._get_default_output_dir()
        )
        if dir_path:
            self._settings.set("default_output_dir", dir_path)
            self.settings_page.output_label.setText(dir_path)
