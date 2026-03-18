from __future__ import annotations

import gc
import logging
from typing import Any, Callable, Iterable, Iterator, Optional

from .capabilities import introspect_capabilities
from .composition import merge_files, parse_page_range, split_file
from .conversion import batch_convert, convert_document
from .fields import detect_pii_patterns, extract_text_for_scan, fill_fields, list_fields, scan_personal_info
from .injection import batch_inject_data, inject_data, iter_inject_data, mail_merge, render_filename_template
from .metadata import get_meta_tags, set_meta_tags
from .security import clean_metadata, harden_document, save_as_with_password
from .types import CapabilitySnapshot, ConversionResult, ConvertFormat, OperationResult


class HwpHandler:
    """
    pyhwpx 래퍼 클래스
    HWP 파일 열기, 변환, 병합, 분할 등의 기능을 제공한다.
    """

    def __init__(self) -> None:
        self._hwp: Any = None
        self._is_initialized = False
        self._logger = logging.getLogger(__name__)

    def _ensure_hwp(self) -> None:
        """pyhwpx 인스턴스 초기화."""

        if self._hwp is None:
            try:
                import pyhwpx

                self._hwp = pyhwpx.Hwp(visible=False)
                self._is_initialized = True
            except ImportError:
                raise RuntimeError("pyhwpx가 설치되어 있지 않습니다. 'pip install pyhwpx'로 설치해주세요.")
            except Exception as e:
                raise RuntimeError(f"한글 프로그램 초기화 실패: {e}")

    def _get_hwp(self) -> Any:
        """초기화된 HWP 인스턴스를 반환한다."""

        self._ensure_hwp()
        if self._hwp is None:
            raise RuntimeError("한글 인스턴스 초기화 실패")
        return self._hwp

    def close(self) -> None:
        """한글 인스턴스를 종료한다."""

        if self._hwp is not None:
            try:
                self._hwp.quit()
            except Exception as e:
                self._logger.warning(f"HWP 종료 중 오류 (무시): {e}")
            finally:
                self._hwp = None
                self._is_initialized = False
                gc.collect()

    def __enter__(self) -> "HwpHandler":
        self._ensure_hwp()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.close()
        return False

    @staticmethod
    def introspect_capabilities() -> CapabilitySnapshot:
        return introspect_capabilities()

    def run_action(self, action_id: str) -> bool:
        """Execute HWP Run action directly."""

        hwp = self._get_hwp()
        action = str(action_id or "").strip()
        if not action:
            raise ValueError("action_id가 비어 있습니다.")
        result = hwp.Run(action)
        return bool(result)

    def execute_action(self, action_id: str, pset_name: str, values: dict[str, Any]) -> bool:
        """Execute HAction with parameter set values."""

        hwp = self._get_hwp()
        action = str(action_id or "").strip()
        set_name = str(pset_name or "").strip()
        if not action:
            raise ValueError("action_id가 비어 있습니다.")
        if not set_name:
            raise ValueError("pset_name이 비어 있습니다.")

        hps = getattr(hwp, "HParameterSet", None)
        if hps is None:
            raise RuntimeError("HParameterSet을 사용할 수 없습니다.")

        pset = getattr(hps, set_name, None)
        if pset is None:
            raise ValueError(f"지원하지 않는 파라미터셋: {set_name}")

        hwp.HAction.GetDefault(action, pset.HSet)
        for key, value in (values or {}).items():
            if hasattr(pset, key):
                setattr(pset, key, value)
        result = hwp.HAction.Execute(action, pset.HSet)
        return bool(result)

    @staticmethod
    def _extract_text_for_scan(hwp: Any) -> str:
        return extract_text_for_scan(hwp)

    @staticmethod
    def _detect_pii_patterns(
        text: str,
        patterns: Optional[dict[str, str]] = None,
        sample_limit: int = 5,
    ) -> tuple[dict[str, int], dict[str, list[str]], int]:
        return detect_pii_patterns(text=text, patterns=patterns, sample_limit=sample_limit)

    @staticmethod
    def _save_as_with_password(
        hwp: Any,
        output_path: str,
        password: str = "",
    ) -> tuple[bool, bool, Optional[str]]:
        return save_as_with_password(hwp=hwp, output_path=output_path, password=password)

    def scan_personal_info(
        self,
        source_path: str,
        *,
        patterns: Optional[dict[str, str]] = None,
        sample_limit: int = 5,
    ) -> OperationResult:
        return scan_personal_info(self, source_path, patterns=patterns, sample_limit=sample_limit)

    def list_fields(self, source_path: str) -> OperationResult:
        return list_fields(self, source_path)

    def fill_fields(
        self,
        source_path: str,
        values: dict[str, Any],
        output_path: Optional[str] = None,
        *,
        ignore_missing: bool = True,
    ) -> OperationResult:
        return fill_fields(
            self,
            source_path,
            values,
            output_path=output_path,
            ignore_missing=ignore_missing,
        )

    def get_meta_tags(
        self,
        source_path: str,
        keys: Optional[list[str]] = None,
    ) -> OperationResult:
        return get_meta_tags(self, source_path, keys=keys)

    def set_meta_tags(
        self,
        source_path: str,
        tags: dict[str, Any],
        output_path: Optional[str] = None,
    ) -> OperationResult:
        return set_meta_tags(self, source_path, tags, output_path=output_path)

    @staticmethod
    def _render_filename_template(
        template: str,
        row_data: dict[str, str],
        index: int,
        fallback_stem: str,
    ) -> str:
        return render_filename_template(template, row_data, index, fallback_stem)

    def mail_merge(
        self,
        template_path: str,
        data_iterable: Iterable[dict[str, str]],
        output_dir: str,
        *,
        filename_field: Optional[str] = None,
        filename_template: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        total_count: Optional[int] = None,
        stop_on_error: bool = False,
    ) -> OperationResult:
        return mail_merge(
            self,
            template_path,
            data_iterable,
            output_dir,
            filename_field=filename_field,
            filename_template=filename_template,
            progress_callback=progress_callback,
            total_count=total_count,
            stop_on_error=stop_on_error,
        )

    def harden_document(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> OperationResult:
        return harden_document(self, source_path, output_path=output_path, options=options)

    def convert_to_pdf(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        return convert_document(self, source_path, ConvertFormat.PDF, output_path)

    def convert_to_txt(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        return convert_document(self, source_path, ConvertFormat.TXT, output_path)

    def convert_to_hwpx(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        return convert_document(self, source_path, ConvertFormat.HWPX, output_path)

    def convert_to_jpg(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        return convert_document(self, source_path, ConvertFormat.JPG, output_path)

    def convert(
        self,
        source_path: str,
        target_format: ConvertFormat,
        output_path: Optional[str] = None,
    ) -> ConversionResult:
        return convert_document(self, source_path, target_format, output_path)

    def _convert(
        self,
        source_path: str,
        target_format: ConvertFormat,
        output_path: Optional[str] = None,
    ) -> ConversionResult:
        return convert_document(self, source_path, target_format, output_path)

    def batch_convert(
        self,
        source_files: list[str],
        target_format: ConvertFormat,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[ConversionResult]:
        return batch_convert(
            self,
            source_files,
            target_format,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

    def merge_files(
        self,
        source_files: list[str],
        output_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> ConversionResult:
        return merge_files(self, source_files, output_path, progress_callback=progress_callback)

    @staticmethod
    def parse_page_range(range_str: str, max_page: int) -> list[int]:
        return parse_page_range(range_str, max_page)

    def split_file(
        self,
        source_path: str,
        page_ranges: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[ConversionResult]:
        return split_file(
            self,
            source_path,
            page_ranges,
            output_dir,
            progress_callback=progress_callback,
        )

    def inject_data(
        self,
        template_path: str,
        data: dict[str, str],
        output_path: str,
    ) -> ConversionResult:
        return inject_data(self, template_path, data, output_path)

    def batch_inject_data(
        self,
        template_path: str,
        data_list: list[dict[str, str]],
        output_dir: str,
        filename_field: Optional[str] = None,
        filename_template: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[ConversionResult]:
        return batch_inject_data(
            self,
            template_path,
            data_list,
            output_dir,
            filename_field=filename_field,
            filename_template=filename_template,
            progress_callback=progress_callback,
        )

    def iter_inject_data(
        self,
        template_path: str,
        data_iterable: Iterable[dict[str, str]],
        output_dir: str,
        filename_field: Optional[str] = None,
        filename_template: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        total_count: Optional[int] = None,
        stats: Optional[dict[str, int]] = None,
    ) -> Iterator[ConversionResult]:
        return iter_inject_data(
            self,
            template_path,
            data_iterable,
            output_dir,
            filename_field=filename_field,
            filename_template=filename_template,
            progress_callback=progress_callback,
            total_count=total_count,
            stats=stats,
        )

    def clean_metadata(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> ConversionResult:
        return clean_metadata(self, source_path, output_path=output_path, options=options)
