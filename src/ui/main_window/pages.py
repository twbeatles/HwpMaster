from __future__ import annotations

from importlib import import_module
from typing import Any

from PySide6.QtWidgets import QVBoxLayout, QWidget


TOTAL_PAGE_COUNT = 19
LAZY_PAGE_SPECS: dict[int, tuple[str, str, str]] = {
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
    17: (".pages.action_console_page", "ActionConsolePage", "action_console_page"),
}


def init_page_stack(window: Any) -> None:
    for index in range(window._TOTAL_PAGE_COUNT):
        if index in window._LAZY_PAGE_SPECS:
            placeholder = create_placeholder_page()
            window.page_stack.addWidget(placeholder)
            window._page_widgets[index] = placeholder
        else:
            page = create_eager_page(window, index)
            window.page_stack.addWidget(page)
            window._page_widgets[index] = page


def create_eager_page(window: Any, index: int) -> QWidget:
    page_map: dict[int, QWidget] = {
        0: window.home_page,
        1: window.convert_page,
        2: window.merge_split_page,
        3: window.data_inject_page,
        4: window.metadata_page,
        18: window.settings_page,
    }
    page = page_map.get(index)
    if page is None:
        raise ValueError(f"Unsupported eager page index: {index}")
    return page


def create_placeholder_page() -> QWidget:
    placeholder = QWidget()
    layout = QVBoxLayout(placeholder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch()
    return placeholder


def ensure_page_loaded(window: Any, index: int) -> None:
    if index not in window._LAZY_PAGE_SPECS or index in window._lazy_loaded:
        return

    module_name, class_name, attr_name = window._LAZY_PAGE_SPECS[index]
    module = import_module(module_name, package="src.ui")
    page_cls = getattr(module, class_name)
    page = page_cls()

    old_widget = window._page_widgets[index]
    window.page_stack.removeWidget(old_widget)
    old_widget.deleteLater()
    window.page_stack.insertWidget(index, page)

    window._page_widgets[index] = page
    setattr(window, attr_name, page)
    bind_lazy_page_signals(window, index, page)
    window._lazy_loaded.add(index)


def bind_lazy_page_signals(window: Any, index: int, page: QWidget) -> None:
    if index in window._lazy_signal_bound:
        return
    window._lazy_signal_bound.add(index)
