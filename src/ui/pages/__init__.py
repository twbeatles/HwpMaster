"""UI pages package with lazy exports.

This keeps public imports stable:
    from src.ui.pages import HomePage
but avoids importing every page module at startup.
"""

from __future__ import annotations

import importlib
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .action_console_page import ActionConsolePage
    from .bookmark_page import BookmarkPage
    from .convert_page import ConvertPage
    from .data_inject_page import DataInjectPage
    from .doc_diff_page import DocDiffPage
    from .header_footer_page import HeaderFooterPage
    from .home_page import HomePage
    from .hyperlink_page import HyperlinkPage
    from .image_extractor_page import ImageExtractorPage
    from .macro_page import MacroPage
    from .merge_split_page import MergeSplitPage
    from .metadata_page import MetadataPage
    from .regex_page import RegexPage
    from .settings_page import SettingsPage
    from .smart_toc_page import SmartTocPage
    from .style_cop_page import StyleCopPage
    from .table_doctor_page import TableDoctorPage
    from .template_page import TemplatePage
    from .watermark_page import WatermarkPage


_PAGE_MODULES: dict[str, str] = {
    "HomePage": ".home_page",
    "ConvertPage": ".convert_page",
    "MergeSplitPage": ".merge_split_page",
    "DataInjectPage": ".data_inject_page",
    "MetadataPage": ".metadata_page",
    "SettingsPage": ".settings_page",
    "TemplatePage": ".template_page",
    "MacroPage": ".macro_page",
    "RegexPage": ".regex_page",
    "StyleCopPage": ".style_cop_page",
    "TableDoctorPage": ".table_doctor_page",
    "DocDiffPage": ".doc_diff_page",
    "SmartTocPage": ".smart_toc_page",
    "WatermarkPage": ".watermark_page",
    "HeaderFooterPage": ".header_footer_page",
    "BookmarkPage": ".bookmark_page",
    "HyperlinkPage": ".hyperlink_page",
    "ImageExtractorPage": ".image_extractor_page",
    "ActionConsolePage": ".action_console_page",
}

__all__ = (
    "HomePage",
    "ConvertPage",
    "MergeSplitPage",
    "DataInjectPage",
    "MetadataPage",
    "SettingsPage",
    "TemplatePage",
    "MacroPage",
    "RegexPage",
    "StyleCopPage",
    "TableDoctorPage",
    "DocDiffPage",
    "SmartTocPage",
    "WatermarkPage",
    "HeaderFooterPage",
    "BookmarkPage",
    "HyperlinkPage",
    "ImageExtractorPage",
    "ActionConsolePage",
)


def __getattr__(name: str) -> Any:
    module_name = _PAGE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = importlib.import_module(module_name, package=__name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(__all__))
