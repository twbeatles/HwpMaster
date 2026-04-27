from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from ..pages.convert_page import ConvertPage
from ..pages.data_inject_page import DataInjectPage
from ..pages.home_page import HomePage
from ..pages.merge_split_page import MergeSplitPage
from ..pages.metadata_page import MetadataPage
from ..pages.settings_page import SettingsPage
from ...utils.history_manager import get_history_manager
from ...utils.worker import WorkerResult
from .operations import (
    apply_theme_preset,
    cancel_current_worker,
    connect_signals,
    on_clean_metadata,
    on_convert,
    on_convert_finished,
    on_hyperlink_allowlist_changed,
    on_hyperlink_timeout_sec_changed,
    on_inject,
    on_inject_finished,
    on_merge_finished,
    on_merge_split,
    on_metadata_finished,
    on_page_changed,
    on_split_finished,
    on_theme_preset_changed,
    select_data_file,
    select_output_dir,
    select_template,
    sync_settings_page,
)
from .pages import LAZY_PAGE_SPECS, TOTAL_PAGE_COUNT, bind_lazy_page_signals, create_eager_page, create_placeholder_page, ensure_page_loaded, init_page_stack
from .sidebar import Sidebar


class MainWindow(QMainWindow):
    """메인 윈도우"""

    _TOTAL_PAGE_COUNT = TOTAL_PAGE_COUNT
    _LAZY_PAGE_SPECS = LAZY_PAGE_SPECS

    def __init__(self) -> None:
        super().__init__()
        import src.ui.main_window as main_window_pkg

        self._settings = main_window_pkg.get_settings_manager()
        self._history = get_history_manager(config_dir=self._settings.config_dir)

        self.setWindowTitle("HWP Master")
        self.setMinimumSize(1200, 800)
        self.resize(
            int(self._settings.get("window_width", 1400)),
            int(self._settings.get("window_height", 900)),
        )

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

        self.home_page = HomePage(settings_manager=self._settings, history_manager=self._history)
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
        self.action_console_page = None
        self.editor_page = None

        self._init_page_stack()
        self._sync_settings_page()
        self._connect_signals()
        self.sidebar.set_collapsed(bool(self._settings.get("sidebar_collapsed", False)), animate=False)

    def _init_page_stack(self) -> None:
        init_page_stack(self)

    def _create_eager_page(self, index: int) -> QWidget:
        return create_eager_page(self, index)

    @staticmethod
    def _create_placeholder_page() -> QWidget:
        return create_placeholder_page()

    def _ensure_page_loaded(self, index: int) -> None:
        ensure_page_loaded(self, index)

    def _bind_lazy_page_signals(self, index: int, page: QWidget) -> None:
        bind_lazy_page_signals(self, index, page)

    def _get_default_output_dir(self) -> str:
        configured = self._settings.get("default_output_dir", "")
        if configured and Path(configured).exists():
            return configured
        fallback = Path.home() / "Documents" / "HWP Master"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            from ...utils.logger import get_logger

            get_logger(__name__).warning(f"기본 출력 폴더 생성 실패(무시): {fallback} ({e})")
        return str(fallback)

    def _sync_settings_page(self) -> None:
        sync_settings_page(self)

    def _apply_theme_preset(self, preset: str) -> None:
        apply_theme_preset(self, preset)

    def _cancel_current_worker(self) -> None:
        cancel_current_worker(self)

    def set_busy(self, busy: bool) -> None:
        self.sidebar.setEnabled(not busy)
        if busy:
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.unsetCursor()

    def _connect_signals(self) -> None:
        connect_signals(self)

    @Slot(str)
    def _on_theme_preset_changed(self, preset: str) -> None:
        on_theme_preset_changed(self, preset)

    @Slot(int)
    def _on_hyperlink_timeout_sec_changed(self, value: int) -> None:
        on_hyperlink_timeout_sec_changed(self, value)

    @Slot(str)
    def _on_hyperlink_allowlist_changed(self, value: str) -> None:
        on_hyperlink_allowlist_changed(self, value)

    @Slot(int)
    def _on_page_changed(self, index: int) -> None:
        on_page_changed(self, index)

    @Slot()
    def _on_convert(self) -> None:
        on_convert(self)

    @Slot(object)
    def _on_convert_finished(self, result: WorkerResult) -> None:
        on_convert_finished(self, result)

    @Slot()
    def _on_merge_split(self) -> None:
        on_merge_split(self)

    @Slot(object)
    def _on_merge_finished(self, result: WorkerResult) -> None:
        on_merge_finished(self, result)

    @Slot(object)
    def _on_split_finished(self, result: WorkerResult) -> None:
        on_split_finished(self, result)

    @Slot()
    def _select_template(self) -> None:
        select_template(self)

    @Slot()
    def _select_data_file(self) -> None:
        select_data_file(self)

    @Slot()
    def _on_inject(self) -> None:
        on_inject(self)

    @Slot(object)
    def _on_inject_finished(self, result: WorkerResult) -> None:
        on_inject_finished(self, result)

    @Slot()
    def _on_clean_metadata(self) -> None:
        on_clean_metadata(self)

    @Slot(object)
    def _on_metadata_finished(self, result: WorkerResult) -> None:
        on_metadata_finished(self, result)

    @Slot()
    def _select_output_dir(self) -> None:
        select_output_dir(self)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self._settings.set("window_width", int(self.width()), defer=True)
            self._settings.set("window_height", int(self.height()), defer=True)
            self._settings.set("sidebar_collapsed", bool(self.sidebar.is_collapsed), defer=True)
            self._settings.flush()
        except Exception:
            pass
        super().closeEvent(event)
