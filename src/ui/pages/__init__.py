"""UI pages package with lazy exports.

This keeps public imports stable:
    from src.ui.pages import HomePage
but avoids importing every page module at startup.
"""

from __future__ import annotations

import importlib
from typing import Any


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
}

__all__ = list(_PAGE_MODULES.keys())


def __getattr__(name: str) -> Any:
    module_name = _PAGE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = importlib.import_module(module_name, package=__name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
