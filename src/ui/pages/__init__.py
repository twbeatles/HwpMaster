# UI Pages Package
from .home_page import HomePage
from .convert_page import ConvertPage
from .merge_split_page import MergeSplitPage
from .data_inject_page import DataInjectPage
from .metadata_page import MetadataPage
from .settings_page import SettingsPage

from .template_page import TemplatePage
from .macro_page import MacroPage
from .regex_page import RegexPage
from .style_cop_page import StyleCopPage
from .table_doctor_page import TableDoctorPage
from .doc_diff_page import DocDiffPage
from .smart_toc_page import SmartTocPage

# Phase 5 Pages
from .watermark_page import WatermarkPage
from .header_footer_page import HeaderFooterPage
from .bookmark_page import BookmarkPage
from .hyperlink_page import HyperlinkPage
from .image_extractor_page import ImageExtractorPage

__all__ = [
    'HomePage',
    'ConvertPage',
    'MergeSplitPage',
    'DataInjectPage',
    'MetadataPage',
    'SettingsPage',
    'TemplatePage', 
    'MacroPage', 
    'RegexPage',
    'StyleCopPage',
    'TableDoctorPage',
    'DocDiffPage',
    'SmartTocPage',
    # Phase 5
    'WatermarkPage',
    'HeaderFooterPage',
    'BookmarkPage',
    'HyperlinkPage',
    'ImageExtractorPage',
]
