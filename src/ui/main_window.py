"""
Main Window Module
PySide6 기반 메인 윈도우 UI

Author: HWP Master
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, Slot, QParallelAnimationGroup
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from .widgets.sidebar_button import SidebarButton
from ..utils.worker import (
    ConversionWorker,
    DataInjectWorker,
    MergeWorker,
    MetadataCleanWorker,
    SplitWorker,
    WorkerResult,
)
from ..utils.settings import get_settings_manager
from ..utils.qss_renderer import build_stylesheet
from ..utils.version import APP_VERSION

from .pages.home_page import HomePage
from .pages.convert_page import ConvertPage
from .pages.merge_split_page import MergeSplitPage
from .pages.data_inject_page import DataInjectPage
from .pages.metadata_page import MetadataPage
from .pages.settings_page import SettingsPage


class Sidebar(QFrame):
    """사이드바 네비게이션"""

    page_changed = Signal(int)

    NAV_SECTIONS = [
        ("기본", [("🏠", "홈"), ("🔄", "변환"), ("🔗", "병합/분할"), ("🧩", "데이터 주입"), ("🧹", "메타정보 정리")]),
        ("고급", [("📁", "템플릿 스토어"), ("🎬", "매크로"), ("🧪", "정규식 치환")]),
        ("분석", [("🕵", "서식 교정"), ("📊", "표 교정"), ("📄", "문서 비교"), ("📚", "스마트 목차")]),
        ("생산성", [("💧", "워터마크"), ("📑", "헤더/푸터"), ("🔖", "북마크"), ("🔍", "링크 검사"), ("🖼", "이미지 추출")]),
        ("", [("⚙", "설정")]),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(280)

        self._is_collapsed = False
        self._buttons: list[SidebarButton] = []
        self._nav_items: list[tuple[str, str]] = []
        self._section_labels: list[QLabel] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 20, 12, 16)
        header_layout.setSpacing(2)

        logo_container = QWidget()
        logo_inner = QHBoxLayout(logo_container)
        logo_inner.setContentsMargins(8, 0, 8, 0)
        logo_inner.setSpacing(12)

        logo_icon = QLabel("📄")
        logo_icon.setStyleSheet("font-size: 28px; background: transparent;")
        logo_inner.addWidget(logo_icon)

        title_container = QWidget()
        title_inner = QVBoxLayout(title_container)
        title_inner.setContentsMargins(0, 0, 0, 0)
        title_inner.setSpacing(0)

        self._title_label = QLabel("HWP Master")
        self._title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #ffffff; background: transparent;")
        title_inner.addWidget(self._title_label)

        try:
            version = QApplication.instance().applicationVersion() if QApplication.instance() else ""
        except Exception:
            version = ""
        self._version_label = QLabel(f"v{version}" if version else f"v{APP_VERSION}")
        self._version_label.setStyleSheet("color: #8957e5; font-size: 11px; background: transparent;")
        title_inner.addWidget(self._version_label)

        logo_inner.addWidget(title_container)
        logo_inner.addStretch()
        header_layout.addWidget(logo_container)
        header_layout.addSpacing(20)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #30363d;")
        header_layout.addWidget(line)

        main_layout.addWidget(header_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 0px; background: transparent; }
            """
        )

        scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(12, 10, 12, 10)
        self._scroll_layout.setSpacing(4)

        btn_index = 0
        for section_name, items in self.NAV_SECTIONS:
            if section_name:
                section_label = QLabel(section_name)
                section_label.setStyleSheet(
                    """
                    color: #484f58;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    padding: 12px 10px 6px 10px;
                    background: transparent;
                    """
                )
                self._section_labels.append(section_label)
                self._scroll_layout.addWidget(section_label)

            for icon, text in items:
                self._nav_items.append((icon, text))
                btn = SidebarButton(f"  {icon}  {text}")
                btn.clicked.connect(lambda checked, i=btn_index: self._on_button_clicked(i))
                self._buttons.append(btn)
                self._scroll_layout.addWidget(btn)
                btn_index += 1

        if self._buttons:
            self._buttons[0].setChecked(True)

        self._scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(12, 10, 12, 16)

        self._toggle_btn = QPushButton("◀  메뉴 접기")
        self._toggle_btn.setMinimumHeight(32)
        self._toggle_btn.setStyleSheet(
            """
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
            """
        )
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        footer_layout.addWidget(self._toggle_btn)

        main_layout.addWidget(footer_widget)

    def _on_button_clicked(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

    def _toggle_collapse(self) -> None:
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
            self._toggle_btn.setStyleSheet(
                self._toggle_btn.styleSheet() + "text-align: center; padding-left: 0px;"
            )
        else:
            self._toggle_btn.setText("◀  메뉴 접기")
            self._toggle_btn.setStyleSheet(
                self._toggle_btn.styleSheet().replace(
                    "text-align: center; padding-left: 0px;",
                    "text-align: left; padding-left: 10px;",
                )
            )

        self._title_label.setVisible(not self._is_collapsed)
        self._version_label.setVisible(not self._is_collapsed)

        for label in self._section_labels:
            label.setVisible(not self._is_collapsed)

        for btn, (icon, text) in zip(self._buttons, self._nav_items):
            if self._is_collapsed:
                btn.setText(f"  {icon}")
                btn.setToolTip(text)
            else:
                btn.setText(f"  {icon}  {text}")
                btn.setToolTip("")


class MainWindow(QMainWindow):
    """메인 윈도우"""

    _TOTAL_PAGE_COUNT = 18
    _LAZY_PAGE_SPECS: dict[int, tuple[str, str, str]] = {
        5: (".pages.template_page", "TemplatePage", "template_page"),
        6: (".pages.macro_page", "MacroPage", "macro_page"),
        7: (".pages.regex_page", "RegexPage", "regex_page"),
        8: (".pages.style_cop_page", "StyleCopPage", "style_cop_page"),
        9: (".pages.table_doctor_page", "TableDoctorPage", "table_doctor_page"),
        10: (".pages.doc_diff_page", "DocDiffPage", "doc_diff_page"),
        11: (".pages.smart_toc_page", "SmartTocPage", "smart_toc_page"),
        12: (".pages.watermark_page", "WatermarkPage", "watermark_page"),
        13: (".pages.header_footer_page", "HeaderFooterPage", "header_footer_page"),
        14: (".pages.bookmark_page", "BookmarkPage", "bookmark_page"),
        15: (".pages.hyperlink_page", "HyperlinkPage", "hyperlink_page"),
        16: (".pages.image_extractor_page", "ImageExtractorPage", "image_extractor_page"),
    }

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings_manager()

        self.setWindowTitle("HWP Master")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self.sidebar)

        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)

        self._current_worker = None
        self._page_widgets: dict[int, QWidget] = {}
        self._lazy_loaded: set[int] = set()
        self._lazy_signal_bound: set[int] = set()

        self.home_page = HomePage()
        self.home_page.card_clicked.connect(self._on_page_changed)
        self.convert_page = ConvertPage()
        self.merge_split_page = MergeSplitPage()
        self.data_inject_page = DataInjectPage()
        self.metadata_page = MetadataPage()
        self.settings_page = SettingsPage()

        self.template_page = None
        self.macro_page = None
        self.regex_page = None
        self.style_cop_page = None
        self.table_doctor_page = None
        self.doc_diff_page = None
        self.smart_toc_page = None
        self.watermark_page = None
        self.header_footer_page = None
        self.bookmark_page = None
        self.hyperlink_page = None
        self.image_extractor_page = None

        self._init_page_stack()
        self._sync_settings_page()
        self._connect_signals()

    def _init_page_stack(self) -> None:
        for index in range(self._TOTAL_PAGE_COUNT):
            if index in self._LAZY_PAGE_SPECS:
                placeholder = self._create_placeholder_page()
                self.page_stack.addWidget(placeholder)
                self._page_widgets[index] = placeholder
            else:
                page = self._create_eager_page(index)
                self.page_stack.addWidget(page)
                self._page_widgets[index] = page

    def _create_eager_page(self, index: int) -> QWidget:
        page_map: dict[int, QWidget] = {
            0: self.home_page,
            1: self.convert_page,
            2: self.merge_split_page,
            3: self.data_inject_page,
            4: self.metadata_page,
            17: self.settings_page,
        }
        page = page_map.get(index)
        if page is None:
            raise ValueError(f"Unsupported eager page index: {index}")
        return page

    @staticmethod
    def _create_placeholder_page() -> QWidget:
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        return placeholder

    def _ensure_page_loaded(self, index: int) -> None:
        if index not in self._LAZY_PAGE_SPECS:
            return
        if index in self._lazy_loaded:
            return

        module_name, class_name, attr_name = self._LAZY_PAGE_SPECS[index]
        module = import_module(module_name, package=__package__)
        page_cls = getattr(module, class_name)
        page = page_cls()

        old_widget = self._page_widgets[index]
        self.page_stack.removeWidget(old_widget)
        old_widget.deleteLater()
        self.page_stack.insertWidget(index, page)

        self._page_widgets[index] = page
        setattr(self, attr_name, page)
        self._bind_lazy_page_signals(index, page)
        self._lazy_loaded.add(index)

    def _bind_lazy_page_signals(self, index: int, page: QWidget) -> None:
        if index in self._lazy_signal_bound:
            return
        # Reserved for per-page lazy signal wiring.
        self._lazy_signal_bound.add(index)

    def _get_default_output_dir(self) -> str:
        configured = self._settings.get("default_output_dir", "")
        if configured and Path(configured).exists():
            return configured
        fallback = Path.home() / "Documents" / "HWP Master"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            from ..utils.logger import get_logger

            get_logger(__name__).warning(f"기본 출력 폴더 생성 실패(무시): {fallback} ({e})")
        return str(fallback)

    def _sync_settings_page(self) -> None:
        default_output_dir = self._settings.get("default_output_dir", "")
        if default_output_dir:
            self.settings_page.output_label.setText(default_output_dir)
            self.convert_page.output_label.setText(default_output_dir)
            self.metadata_page.output_label.setText(default_output_dir)
            self.data_inject_page.output_label.setText(default_output_dir)

        preset = self._settings.get("theme_preset", "Dark (기본)")
        if hasattr(self.settings_page, "theme_combo"):
            idx = self.settings_page.theme_combo.findText(preset)
            if idx >= 0:
                self.settings_page.theme_combo.setCurrentIndex(idx)

        if hasattr(self.settings_page, "hyperlink_external_checkbox"):
            cb = self.settings_page.hyperlink_external_checkbox
            cb.blockSignals(True)
            cb.setChecked(bool(self._settings.get("hyperlink_external_requests_enabled", True)))
            cb.blockSignals(False)

        if hasattr(self.settings_page, "hyperlink_timeout_spin"):
            sp = self.settings_page.hyperlink_timeout_spin
            sp.blockSignals(True)
            try:
                sp.setValue(int(self._settings.get("hyperlink_timeout_sec", 5)))
            except Exception:
                sp.setValue(5)
            sp.blockSignals(False)

        if hasattr(self.settings_page, "hyperlink_allowlist_edit"):
            ed = self.settings_page.hyperlink_allowlist_edit
            ed.blockSignals(True)
            ed.setText(str(self._settings.get("hyperlink_domain_allowlist", "")))
            ed.blockSignals(False)

    def _apply_theme_preset(self, preset: str) -> None:
        try:
            app = QApplication.instance()
            if app is None:
                return
            app.setStyleSheet(build_stylesheet(preset))
        except Exception as e:
            from ..utils.logger import get_logger

            get_logger(__name__).warning(f"테마 적용 실패: {e}")

    def _cancel_current_worker(self) -> None:
        if self._current_worker is not None:
            try:
                self._current_worker.cancel()
            except Exception as e:
                from ..utils.logger import get_logger

                get_logger(__name__).warning(f"worker.cancel() 호출 실패(무시): {e}")

    def set_busy(self, busy: bool) -> None:
        self.sidebar.setEnabled(not busy)
        if busy:
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.unsetCursor()

    def _connect_signals(self) -> None:
        self.convert_page.convert_btn.clicked.connect(self._on_convert)
        self.convert_page.output_btn.clicked.connect(self._select_output_dir)
        self.convert_page.progress_card.cancelled.connect(self._cancel_current_worker)

        self.merge_split_page.execute_btn.clicked.connect(self._on_merge_split)
        self.merge_split_page.progress_card.cancelled.connect(self._cancel_current_worker)

        self.data_inject_page.template_btn.clicked.connect(self._select_template)
        self.data_inject_page.data_btn.clicked.connect(self._select_data_file)
        self.data_inject_page.execute_btn.clicked.connect(self._on_inject)
        self.data_inject_page.output_btn.clicked.connect(self._select_output_dir)
        self.data_inject_page.progress_card.cancelled.connect(self._cancel_current_worker)

        self.metadata_page.execute_btn.clicked.connect(self._on_clean_metadata)
        self.metadata_page.output_btn.clicked.connect(self._select_output_dir)
        self.metadata_page.progress_card.cancelled.connect(self._cancel_current_worker)

        self.settings_page.output_btn.clicked.connect(self._select_output_dir)
        if hasattr(self.settings_page, "theme_preset_changed"):
            self.settings_page.theme_preset_changed.connect(self._on_theme_preset_changed)
        if hasattr(self.settings_page, "hyperlink_external_requests_enabled_changed"):
            self.settings_page.hyperlink_external_requests_enabled_changed.connect(
                lambda v: self._settings.set("hyperlink_external_requests_enabled", bool(v))
            )
        if hasattr(self.settings_page, "hyperlink_timeout_sec_changed"):
            self.settings_page.hyperlink_timeout_sec_changed.connect(self._on_hyperlink_timeout_sec_changed)
        if hasattr(self.settings_page, "hyperlink_domain_allowlist_changed"):
            self.settings_page.hyperlink_domain_allowlist_changed.connect(self._on_hyperlink_allowlist_changed)

    @Slot(str)
    def _on_theme_preset_changed(self, preset: str) -> None:
        self._settings.set("theme_preset", preset)
        self._apply_theme_preset(preset)

    @Slot(int)
    def _on_hyperlink_timeout_sec_changed(self, value: int) -> None:
        self._settings.set("hyperlink_timeout_sec", int(value), defer=True)

    @Slot(str)
    def _on_hyperlink_allowlist_changed(self, value: str) -> None:
        self._settings.set("hyperlink_domain_allowlist", str(value), defer=True)

    @Slot(int)
    def _on_page_changed(self, index: int) -> None:
        if not (0 <= index < self._TOTAL_PAGE_COUNT):
            return
        self._ensure_page_loaded(index)
        self.page_stack.setCurrentIndex(index)

    @Slot()
    def _on_convert(self) -> None:
        files = self.convert_page.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "알림", "변환할 파일을 추가해주세요.")
            return

        target_format = "PDF"
        for btn in self.convert_page.format_buttons:
            if btn.isChecked():
                target_format = btn.text()
                break

        self.convert_page.progress_card.setVisible(True)
        self.convert_page.progress_card.set_status("변환 준비 중...")
        self.convert_page.convert_btn.setEnabled(False)
        self.convert_page.progress_card.reset()

        self.set_busy(True)
        out_dir = str(Path(self._get_default_output_dir()) / "converted" / target_format.lower())
        self._current_worker = ConversionWorker(files, target_format, output_dir=out_dir)
        self._current_worker.progress.connect(
            lambda c, t, n: (
                self.convert_page.progress_card.set_count(c, t),
                self.convert_page.progress_card.set_current_file(n),
            )
        )
        self._current_worker.status_changed.connect(lambda s: self.convert_page.progress_card.set_status(s))
        self._current_worker.finished_with_result.connect(self._on_convert_finished)
        self._current_worker.start()

    @Slot(object)
    def _on_convert_finished(self, result: WorkerResult) -> None:
        self.set_busy(False)
        self.convert_page.convert_btn.setEnabled(True)
        if result.data and result.data.get("cancelled"):
            self.convert_page.progress_card.set_error("작업이 취소되었습니다.")
            QMessageBox.information(self, "취소", "변환 작업이 취소되었습니다.")
            return

        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.convert_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self,
                "완료",
                f"변환이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개",
            )
        else:
            self.convert_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "변환 중 오류가 발생했습니다.")

    @Slot()
    def _on_merge_split(self) -> None:
        files = self.merge_split_page.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "알림", "파일을 추가해주세요.")
            return

        is_merge = self.merge_split_page.merge_btn.isChecked()

        self.merge_split_page.progress_card.setVisible(True)
        self.merge_split_page.progress_card.set_status("처리 준비 중...")
        self.merge_split_page.execute_btn.setEnabled(False)

        if is_merge:
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "병합 파일 저장",
                str(Path(self._get_default_output_dir()) / "merged.hwp"),
                "HWP 파일 (*.hwp)",
            )
            if not output_path:
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return

            self.set_busy(True)
            self._current_worker = MergeWorker(files, output_path)
            self._current_worker.progress.connect(lambda c, t, n: self.merge_split_page.progress_card.set_count(c, t))
            self._current_worker.finished_with_result.connect(self._on_merge_finished)
            self._current_worker.start()
        else:
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

            output_dir = QFileDialog.getExistingDirectory(self, "분할 파일 저장 위치", self._get_default_output_dir())
            if not output_dir:
                self.merge_split_page.execute_btn.setEnabled(True)
                self.merge_split_page.progress_card.setVisible(False)
                return

            self.set_busy(True)
            self._current_worker = SplitWorker(files[0], page_ranges, output_dir)
            self._current_worker.progress.connect(lambda c, t, n: self.merge_split_page.progress_card.set_count(c, t))
            self._current_worker.status_changed.connect(lambda s: self.merge_split_page.progress_card.set_status(s))
            self._current_worker.finished_with_result.connect(self._on_split_finished)
            self._current_worker.start()

    @Slot(object)
    def _on_merge_finished(self, result: WorkerResult) -> None:
        self.set_busy(False)
        self.merge_split_page.execute_btn.setEnabled(True)
        if result.data and result.data.get("cancelled"):
            self.merge_split_page.progress_card.set_error("작업이 취소되었습니다.")
            QMessageBox.information(self, "취소", "병합 작업이 취소되었습니다.")
            return

        if result.success:
            self.merge_split_page.progress_card.set_completed(1, 0)
            QMessageBox.information(self, "완료", "파일 병합이 완료되었습니다.")
        else:
            self.merge_split_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "병합 중 오류가 발생했습니다.")

    @Slot(object)
    def _on_split_finished(self, result: WorkerResult) -> None:
        self.set_busy(False)
        self.merge_split_page.execute_btn.setEnabled(True)
        if result.data and result.data.get("cancelled"):
            self.merge_split_page.progress_card.set_error("작업이 취소되었습니다.")
            QMessageBox.information(self, "취소", "분할 작업이 취소되었습니다.")
            return

        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.merge_split_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self,
                "완료",
                f"파일 분할이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개",
            )
        else:
            self.merge_split_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "분할 중 오류가 발생했습니다.")

    @Slot()
    def _select_template(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "템플릿 파일 선택",
            self._get_default_output_dir(),
            "HWP 파일 (*.hwp *.hwpx)",
        )
        if file_path:
            self.data_inject_page.template_label.setText(file_path)
            self.data_inject_page.template_label.setStyleSheet("color: #e8e8e8;")

    @Slot()
    def _select_data_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "데이터 파일 선택",
            self._get_default_output_dir(),
            "Excel 파일 (*.xlsx *.xls);;CSV 파일 (*.csv)",
        )
        if file_path:
            self.data_inject_page.data_label.setText(file_path)
            self.data_inject_page.data_label.setStyleSheet("color: #e8e8e8;")

    @Slot()
    def _on_inject(self) -> None:
        template = self.data_inject_page.template_label.text()
        data_file = self.data_inject_page.data_label.text()

        if "선택된 파일 없음" in template:
            QMessageBox.warning(self, "알림", "템플릿 파일을 선택해주세요.")
            return

        if "선택된 파일 없음" in data_file:
            QMessageBox.warning(self, "알림", "데이터 파일을 선택해주세요.")
            return

        output_dir = str(Path(self._get_default_output_dir()) / "data_injected")
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "오류", f"출력 폴더 생성 실패:\n{output_dir}\n\n{e}")
            return

        self.data_inject_page.progress_card.setVisible(True)
        self.data_inject_page.progress_card.reset()
        self.data_inject_page.progress_card.set_status("문서 생성 중...")
        self.data_inject_page.execute_btn.setEnabled(False)

        self.set_busy(True)
        self._current_worker = DataInjectWorker(template, data_file, output_dir)
        self._current_worker.progress.connect(
            lambda c, t, n: (
                self.data_inject_page.progress_card.set_count(c, t),
                self.data_inject_page.progress_card.set_current_file(n),
            )
        )
        self._current_worker.status_changed.connect(lambda s: self.data_inject_page.progress_card.set_status(s))
        self._current_worker.finished_with_result.connect(self._on_inject_finished)
        self._current_worker.start()

    @Slot(object)
    def _on_inject_finished(self, result: WorkerResult) -> None:
        self.set_busy(False)
        self.data_inject_page.execute_btn.setEnabled(True)
        if result.data and result.data.get("cancelled"):
            self.data_inject_page.progress_card.set_error("작업이 취소되었습니다.")
            QMessageBox.information(self, "취소", "데이터 주입 작업이 취소되었습니다.")
            return

        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.data_inject_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self,
                "완료",
                f"데이터 주입이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개",
            )
        else:
            self.data_inject_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "데이터 주입 중 오류가 발생했습니다.")

    @Slot()
    def _on_clean_metadata(self) -> None:
        files = self.metadata_page.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "알림", "파일을 추가해주세요.")
            return

        self.metadata_page.progress_card.setVisible(True)
        self.metadata_page.progress_card.set_status("메타정보 정리 중...")
        self.metadata_page.execute_btn.setEnabled(False)

        self.set_busy(True)
        out_dir = str(Path(self._get_default_output_dir()) / "metadata_cleaned")
        self._current_worker = MetadataCleanWorker(files, output_dir=out_dir)
        self._current_worker.progress.connect(lambda c, t, n: self.metadata_page.progress_card.set_count(c, t))
        self._current_worker.status_changed.connect(lambda s: self.metadata_page.progress_card.set_status(s))
        self._current_worker.finished_with_result.connect(self._on_metadata_finished)
        self._current_worker.start()

    @Slot(object)
    def _on_metadata_finished(self, result: WorkerResult) -> None:
        self.set_busy(False)
        self.metadata_page.execute_btn.setEnabled(True)
        if result.data and result.data.get("cancelled"):
            self.metadata_page.progress_card.set_error("작업이 취소되었습니다.")
            QMessageBox.information(self, "취소", "메타정보 정리 작업이 취소되었습니다.")
            return

        if result.success:
            data = result.data or {}
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            self.metadata_page.progress_card.set_completed(success_count, fail_count)
            QMessageBox.information(
                self,
                "완료",
                f"메타정보 정리가 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개",
            )
        else:
            self.metadata_page.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "메타정보 정리 중 오류가 발생했습니다.")

    @Slot()
    def _select_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "출력 폴더 선택", self._get_default_output_dir())
        if dir_path:
            self._settings.set("default_output_dir", dir_path)
            self.settings_page.output_label.setText(dir_path)
            self.convert_page.output_label.setText(dir_path)
            self.metadata_page.output_label.setText(dir_path)
            self.data_inject_page.output_label.setText(dir_path)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self._settings.flush()
        except Exception:
            pass
        super().closeEvent(event)
