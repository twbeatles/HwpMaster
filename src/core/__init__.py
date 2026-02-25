# Core Module - HWP and Excel Handlers
from .hwp_handler import HwpHandler, OperationResult, CapabilitySnapshot
from .excel_handler import ExcelHandler
from .template_store import TemplateStore
from .macro_recorder import MacroRecorder
from .regex_replacer import RegexReplacer
from .style_cop import StyleCop
from .table_doctor import TableDoctor
from .doc_diff import DocDiff
from .smart_toc import SmartTOC
from .action_runner import ActionRunner, ActionPreset
from .capability_mapper import CapabilityMapper

# Phase 5 - Productivity
from .watermark_manager import WatermarkManager
from .header_footer_manager import HeaderFooterManager
from .bookmark_manager import BookmarkManager
from .hyperlink_checker import HyperlinkChecker
from .image_extractor import ImageExtractor

__all__ = [
    'HwpHandler', 
    'OperationResult',
    'CapabilitySnapshot',
    'ExcelHandler',
    'TemplateStore',
    'MacroRecorder',
    'RegexReplacer',
    'StyleCop',
    'TableDoctor',
    'DocDiff',
    'SmartTOC',
    'ActionRunner',
    'ActionPreset',
    'CapabilityMapper',
    # Phase 5
    'WatermarkManager',
    'HeaderFooterManager',
    'BookmarkManager',
    'HyperlinkChecker',
    'ImageExtractor',
]
