"""
HWP Handler Module
pyhwpx 래퍼 클래스 - HWP 파일 제어

Author: HWP Master
"""

import os
import gc
import re
import logging
from pathlib import Path
from typing import Optional, Callable, Any, Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum


class ConvertFormat(Enum):
    """변환 형식 열거형."""
    PDF = "pdf"
    TXT = "txt"
    HWPX = "hwpx"
    JPG = "jpg"
    HTML = "html"


@dataclass
class ConversionResult:
    """변환 결과 데이터 클래스."""
    success: bool
    source_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class OperationResult:
    """Generic operation result for action APIs."""
    success: bool
    warnings: list[str] = field(default_factory=list)
    changed_count: int = 0
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class CapabilitySnapshot:
    """pyhwpx capability snapshot."""
    pyhwpx_version: str
    method_count: int
    methods: list[str]
    action_count: int
    actions: list[str]
    categories: dict[str, int] = field(default_factory=dict)
    unsupported_categories: list[str] = field(default_factory=list)


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

    def __enter__(self):
        self._ensure_hwp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @staticmethod
    def introspect_capabilities() -> CapabilitySnapshot:
        """Inspect pyhwpx capabilities without opening a document."""
        categories: dict[str, int] = {
            "file_io": 0,
            "field_form": 0,
            "find_replace": 0,
            "style_format": 0,
            "table": 0,
            "shape_graphic": 0,
            "security_privacy": 0,
            "automation_macro": 0,
            "navigation_selection": 0,
            "other": 0,
        }
        unsupported: list[str] = []

        try:
            import pyhwpx  # type: ignore

            names = sorted(n for n in dir(pyhwpx.Hwp) if not n.startswith("_"))

            for name in names:
                lowered = name.lower()
                if lowered.startswith(("file", "open", "save", "close", "quit")):
                    categories["file_io"] += 1
                elif "field" in lowered or "metatag" in lowered or lowered.startswith("form"):
                    categories["field_form"] += 1
                elif "find" in lowered or "replace" in lowered:
                    categories["find_replace"] += 1
                elif "charshape" in lowered or "parashape" in lowered or "style" in lowered:
                    categories["style_format"] += 1
                elif "table" in lowered or "cell" in lowered:
                    categories["table"] += 1
                elif "shape" in lowered or "draw" in lowered or "picture" in lowered or "image" in lowered:
                    categories["shape_graphic"] += 1
                elif (
                    "private" in lowered
                    or "encrypt" in lowered
                    or "distribution" in lowered
                    or "trackchange" in lowered
                ):
                    categories["security_privacy"] += 1
                elif "macro" in lowered or "script" in lowered:
                    categories["automation_macro"] += 1
                elif lowered.startswith(("move", "goto", "select")):
                    categories["navigation_selection"] += 1
                else:
                    categories["other"] += 1

            for key in ("security_privacy", "automation_macro", "field_form", "table", "shape_graphic"):
                if categories.get(key, 0) == 0:
                    unsupported.append(key)

            return CapabilitySnapshot(
                pyhwpx_version=str(getattr(pyhwpx, "__version__", "unknown")),
                method_count=len(names),
                methods=names,
                action_count=sum(1 for n in names if n[:1].isupper()),
                actions=[n for n in names if n[:1].isupper()],
                categories=categories,
                unsupported_categories=unsupported,
            )
        except Exception:
            unsupported = [k for k in categories.keys() if k != "other"]
            return CapabilitySnapshot(
                pyhwpx_version="unknown",
                method_count=0,
                methods=[],
                action_count=0,
                actions=[],
                categories=categories,
                unsupported_categories=unsupported,
            )

    def run_action(self, action_id: str) -> bool:
        """
        Execute HWP Run action directly.

        Returns:
            True if action returns a truthy result.
        """
        hwp = self._get_hwp()
        action = str(action_id or "").strip()
        if not action:
            raise ValueError("action_id가 비어 있습니다.")
        result = hwp.Run(action)
        return bool(result)

    def execute_action(self, action_id: str, pset_name: str, values: dict[str, Any]) -> bool:
        """
        Execute HAction with parameter set values.

        Example:
            execute_action("InsertText", "HInsertText", {"Text": "hello"})
        """
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
        """Extract plain text from current document for PII scanning."""
        candidates = (
            ("GetTextFile", ("TEXT", ""), {}),
            ("get_text_file", ("TEXT", ""), {}),
            ("GetText", tuple(), {}),
            ("get_text", tuple(), {}),
        )
        for method_name, args, kwargs in candidates:
            method = getattr(hwp, method_name, None)
            if not callable(method):
                continue
            try:
                value = method(*args, **kwargs)
                return str(value or "")
            except Exception:
                continue
        return ""

    @staticmethod
    def _detect_pii_patterns(
        text: str,
        patterns: Optional[dict[str, str]] = None,
        sample_limit: int = 5,
    ) -> tuple[dict[str, int], dict[str, list[str]], int]:
        default_patterns = {
            "resident_id": r"\b\d{6}-\d{7}\b",
            "phone": r"\b(?:01[0-9]|0[2-9]\d?)-?\d{3,4}-?\d{4}\b",
            "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b",
            "card_number": r"\b\d{4}-?\d{4}-?\d{4}-?\d{4}\b",
            "account_number": r"\b\d{2,6}-\d{2,6}-\d{2,6}\b",
        }
        merged_patterns = default_patterns.copy()
        for key, value in (patterns or {}).items():
            if key and value:
                merged_patterns[str(key)] = str(value)

        counts: dict[str, int] = {}
        samples: dict[str, list[str]] = {}
        total = 0

        for key, pattern in merged_patterns.items():
            try:
                compiled = re.compile(pattern)
            except re.error:
                counts[key] = 0
                samples[key] = []
                continue

            matches = list(compiled.finditer(text))
            counts[key] = len(matches)
            total += len(matches)

            sample_values: list[str] = []
            for match in matches:
                token = str(match.group(0) or "").strip()
                if not token:
                    continue
                if token in sample_values:
                    continue
                sample_values.append(token)
                if len(sample_values) >= max(1, int(sample_limit)):
                    break
            samples[key] = sample_values

        return counts, samples, total

    @staticmethod
    def _save_as_with_password(
        hwp: Any,
        output_path: str,
        password: str = "",
    ) -> tuple[bool, bool, Optional[str]]:
        """
        Save document, trying password variants when requested.

        Returns:
            (saved_ok, password_applied, warning_message)
        """
        password_value = str(password or "").strip()
        if not password_value:
            hwp.save_as(output_path)
            return True, False, None

        # 1) Try save_as keyword variants first.
        for kw in ("password", "passwd", "security_password"):
            try:
                hwp.save_as(output_path, **{kw: password_value})
                return True, True, None
            except TypeError:
                continue
            except Exception:
                continue

        # 2) Try dedicated password/encryption methods.
        for method_name in (
            "set_password",
            "set_document_password",
            "set_file_password",
            "set_encrypt_password",
            "encrypt_document",
        ):
            method = getattr(hwp, method_name, None)
            if not callable(method):
                continue
            try:
                method(password_value)
                hwp.save_as(output_path)
                return True, True, None
            except Exception:
                continue

        # 3) Fallback save without password (best effort).
        hwp.save_as(output_path)
        return True, False, "암호 설정 API를 찾지 못해 암호 없이 저장했습니다."

    def scan_personal_info(
        self,
        source_path: str,
        *,
        patterns: Optional[dict[str, str]] = None,
        sample_limit: int = 5,
    ) -> OperationResult:
        """
        Scan a document for personal-information patterns.
        """
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)
            text = self._extract_text_for_scan(hwp)
            if not text:
                return OperationResult(
                    success=True,
                    warnings=["문서 텍스트를 추출하지 못해 스캔 결과가 비어 있습니다."],
                    changed_count=0,
                    artifacts={"matches": {}, "samples": {}, "total": 0},
                )

            counts, samples, total = self._detect_pii_patterns(
                text=text,
                patterns=patterns,
                sample_limit=sample_limit,
            )
            return OperationResult(
                success=True,
                changed_count=total,
                artifacts={
                    "matches": counts,
                    "samples": samples,
                    "total": total,
                },
            )
        except Exception as e:
            return OperationResult(success=False, error=str(e))

    def list_fields(self, source_path: str) -> OperationResult:
        """
        Return field names from a document.
        """
        warnings: list[str] = []
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            raw: Any = None
            for method_name in ("get_field_list", "GetFieldList", "field_list", "FieldList"):
                method_or_value = getattr(hwp, method_name, None)
                if method_or_value is None:
                    continue
                try:
                    raw = method_or_value() if callable(method_or_value) else method_or_value
                    break
                except Exception as e:
                    warnings.append(f"{method_name} 호출 실패: {e}")

            fields: list[str] = []
            if isinstance(raw, str):
                tokens = re.split(r"[\n,;|\x02]+", raw)
                fields = [token.strip() for token in tokens if token and token.strip()]
            elif isinstance(raw, dict):
                fields = [str(k).strip() for k in raw.keys() if str(k).strip()]
            elif isinstance(raw, (list, tuple, set)):
                fields = [str(item).strip() for item in raw if str(item).strip()]

            # Deduplicate while preserving order.
            deduped: list[str] = []
            seen: set[str] = set()
            for field_name in fields:
                if field_name in seen:
                    continue
                seen.add(field_name)
                deduped.append(field_name)

            if not deduped:
                warnings.append("필드 목록을 찾지 못했습니다.")

            return OperationResult(
                success=True,
                warnings=warnings,
                changed_count=len(deduped),
                artifacts={"fields": deduped},
            )
        except Exception as e:
            return OperationResult(success=False, warnings=warnings, error=str(e))

    def fill_fields(
        self,
        source_path: str,
        values: dict[str, Any],
        output_path: Optional[str] = None,
        *,
        ignore_missing: bool = True,
    ) -> OperationResult:
        """
        Fill field values in a document and save it.
        """
        warnings: list[str] = []
        updated_fields: list[str] = []
        missing_fields: list[str] = []

        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            for field_name, value in (values or {}).items():
                applied = False
                str_value = str(value)
                for method_name in (
                    "put_field_text",
                    "PutFieldText",
                    "set_field_text",
                    "SetFieldText",
                ):
                    method = getattr(hwp, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        method(str(field_name), str_value)
                        applied = True
                        updated_fields.append(str(field_name))
                        break
                    except Exception:
                        continue

                if not applied:
                    missing_fields.append(str(field_name))

            save_path = output_path if output_path else source_path
            hwp.save_as(save_path)

            if missing_fields:
                warnings.append(f"일부 필드를 찾지 못했습니다: {', '.join(missing_fields)}")

            success = True
            if not ignore_missing and missing_fields:
                success = False
            if not updated_fields and values:
                success = False

            return OperationResult(
                success=success,
                warnings=warnings,
                changed_count=len(updated_fields),
                artifacts={
                    "output_path": save_path,
                    "updated_fields": updated_fields,
                    "missing_fields": missing_fields,
                },
                error=None if success else "필드 반영에 실패한 항목이 있습니다.",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                warnings=warnings,
                changed_count=len(updated_fields),
                artifacts={
                    "updated_fields": updated_fields,
                    "missing_fields": missing_fields,
                },
                error=str(e),
            )

    def get_meta_tags(
        self,
        source_path: str,
        keys: Optional[list[str]] = None,
    ) -> OperationResult:
        """
        Read document meta tags (best effort across pyhwpx versions).
        """
        warnings: list[str] = []
        tags: dict[str, str] = {}
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            key_list = [str(k) for k in (keys or []) if str(k).strip()]
            if key_list:
                for key in key_list:
                    value: Optional[str] = None
                    for method_name in ("get_metatag", "GetMetaTag", "get_meta_tag"):
                        method = getattr(hwp, method_name, None)
                        if not callable(method):
                            continue
                        try:
                            value = str(method(key))
                            break
                        except Exception:
                            continue
                    if value is not None and value != "None":
                        tags[key] = value
                    else:
                        warnings.append(f"메타태그 조회 실패: {key}")
            else:
                raw: Any = None
                for method_name in (
                    "get_metatag_all",
                    "GetMetaTagAll",
                    "get_meta_tags",
                    "get_metatags",
                ):
                    method = getattr(hwp, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        raw = method()
                        break
                    except Exception:
                        continue

                if isinstance(raw, dict):
                    tags = {str(k): str(v) for k, v in raw.items()}
                elif isinstance(raw, (list, tuple)):
                    for item in raw:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            tags[str(item[0])] = str(item[1])
                elif raw is None:
                    warnings.append("메타태그 조회 API를 찾지 못했습니다.")

            return OperationResult(
                success=True,
                warnings=warnings,
                changed_count=len(tags),
                artifacts={"meta_tags": tags},
            )
        except Exception as e:
            return OperationResult(success=False, warnings=warnings, error=str(e))

    def set_meta_tags(
        self,
        source_path: str,
        tags: dict[str, Any],
        output_path: Optional[str] = None,
    ) -> OperationResult:
        """
        Set document meta tags (best effort across pyhwpx versions).
        """
        warnings: list[str] = []
        updated: list[str] = []
        failed: list[str] = []

        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            for key, value in (tags or {}).items():
                applied = False
                for method_name in (
                    "set_metatag",
                    "SetMetaTag",
                    "put_metatag",
                    "put_meta_tag",
                    "set_meta_tag",
                ):
                    method = getattr(hwp, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        method(str(key), str(value))
                        applied = True
                        break
                    except Exception:
                        continue

                if not applied and hasattr(hwp, "set_document_info"):
                    try:
                        hwp.set_document_info(str(key), str(value))
                        applied = True
                    except Exception:
                        applied = False

                if applied:
                    updated.append(str(key))
                else:
                    failed.append(str(key))

            save_path = output_path if output_path else source_path
            hwp.save_as(save_path)

            if failed:
                warnings.append(f"일부 메타태그를 반영하지 못했습니다: {', '.join(failed)}")

            success = len(failed) == 0 or len(updated) > 0
            return OperationResult(
                success=success,
                warnings=warnings,
                changed_count=len(updated),
                artifacts={
                    "output_path": save_path,
                    "updated_keys": updated,
                    "failed_keys": failed,
                },
                error=None if success else "메타태그 반영 실패",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                warnings=warnings,
                changed_count=len(updated),
                artifacts={"updated_keys": updated, "failed_keys": failed},
                error=str(e),
            )

    @staticmethod
    def _render_filename_template(
        template: str,
        row_data: dict[str, str],
        index: int,
        fallback_stem: str,
    ) -> str:
        class _SafeDict(dict[str, str]):
            def __missing__(self, key: str) -> str:
                return ""

        data = {str(k): str(v) for k, v in (row_data or {}).items()}
        data.setdefault("index", f"{index:04d}")
        data.setdefault("_index", str(index))
        rendered = str(template or "").strip()
        if not rendered:
            return f"{fallback_stem}_{index:04d}"
        try:
            rendered = rendered.format_map(_SafeDict(data))
        except Exception:
            rendered = f"{fallback_stem}_{index:04d}"
        return rendered or f"{fallback_stem}_{index:04d}"

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
        """
        Mail-merge wrapper that returns a rich operation summary.
        """
        success_count = 0
        fail_count = 0
        warnings: list[str] = []
        outputs: list[str] = []
        failed_outputs: list[dict[str, str]] = []

        try:
            for idx, result in enumerate(
                self.iter_inject_data(
                    template_path=template_path,
                    data_iterable=data_iterable,
                    output_dir=output_dir,
                    filename_field=filename_field,
                    filename_template=filename_template,
                    progress_callback=progress_callback,
                    total_count=total_count,
                ),
                start=1,
            ):
                if result.success:
                    success_count += 1
                    if result.output_path:
                        outputs.append(result.output_path)
                else:
                    fail_count += 1
                    failed_outputs.append(
                        {
                            "index": str(idx),
                            "error": str(result.error_message or "unknown"),
                        }
                    )
                    warnings.append(f"{idx}번째 데이터 행 처리 실패")
                    if stop_on_error:
                        break

            return OperationResult(
                success=fail_count == 0,
                warnings=warnings,
                changed_count=success_count,
                artifacts={
                    "output_dir": str(Path(output_dir)),
                    "outputs": outputs,
                    "failed": failed_outputs,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
                error=failed_outputs[0]["error"] if failed_outputs else None,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                warnings=warnings,
                changed_count=success_count,
                artifacts={
                    "output_dir": str(Path(output_dir)),
                    "outputs": outputs,
                    "failed": failed_outputs,
                    "success_count": success_count,
                    "fail_count": fail_count,
                },
                error=str(e),
            )

    def harden_document(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> OperationResult:
        """
        Security/privacy hardening in one pass.

        Supported options:
            - remove_author: bool
            - remove_comments: bool
            - remove_tracking: bool
            - set_distribution: bool
            - scan_personal_info: bool
            - pii_patterns: dict[str, str]
            - pii_sample_limit: int
            - document_password: str
            - strict_password: bool
        """
        merged: dict[str, Any] = {
            "remove_author": True,
            "remove_comments": True,
            "remove_tracking": True,
            "set_distribution": True,
            "scan_personal_info": False,
            "pii_patterns": None,
            "pii_sample_limit": 5,
            "document_password": "",
            "strict_password": False,
        }
        if options:
            merged.update(options)

        warnings: list[str] = []
        changed_count = 0
        artifacts: dict[str, Any] = {}

        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            if bool(merged.get("scan_personal_info", False)):
                text = self._extract_text_for_scan(hwp)
                pii_counts, pii_samples, pii_total = self._detect_pii_patterns(
                    text=text,
                    patterns=merged.get("pii_patterns"),
                    sample_limit=int(merged.get("pii_sample_limit", 5) or 5),
                )
                artifacts["pii_counts"] = pii_counts
                artifacts["pii_samples"] = pii_samples
                artifacts["pii_total"] = pii_total
                if pii_total > 0:
                    warnings.append(f"개인정보 패턴 {pii_total}건 탐지")

            if bool(merged.get("remove_author", True)):
                try:
                    if hasattr(hwp, "set_document_info"):
                        hwp.set_document_info("author", "")
                        hwp.set_document_info("company", "")
                        changed_count += 1
                    else:
                        warnings.append("작성자 정보 제거 API를 찾지 못했습니다.")
                except Exception as e:
                    warnings.append(f"작성자 정보 제거 실패: {e}")

            if bool(merged.get("remove_comments", True)):
                removed = False
                for method_name in ("delete_all_comments", "DeleteAllComments", "DeleteAllComment"):
                    method = getattr(hwp, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        method()
                        removed = True
                        changed_count += 1
                        break
                    except Exception:
                        continue
                if not removed:
                    warnings.append("메모 제거 API를 찾지 못했습니다.")

            if bool(merged.get("remove_tracking", True)):
                accepted = False
                for method_name in ("accept_all_changes", "AcceptAllChanges", "AcceptAllChange"):
                    method = getattr(hwp, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        method()
                        accepted = True
                        changed_count += 1
                        break
                    except Exception:
                        continue
                if not accepted:
                    warnings.append("변경 추적 정리 API를 찾지 못했습니다.")

            if bool(merged.get("set_distribution", True)):
                distribution_set = False
                for method_name in ("set_distribution_mode", "SetDistributionMode"):
                    method = getattr(hwp, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        method(True)
                        distribution_set = True
                        changed_count += 1
                        break
                    except Exception:
                        continue
                if not distribution_set:
                    warnings.append("배포용 문서 설정 API를 찾지 못했습니다.")

            save_path = output_path if output_path else source_path
            password = str(merged.get("document_password", "") or "").strip()
            strict_password = bool(merged.get("strict_password", False))
            saved_ok, password_applied, save_warning = self._save_as_with_password(
                hwp=hwp,
                output_path=save_path,
                password=password,
            )
            artifacts["output_path"] = save_path
            artifacts["password_requested"] = bool(password)
            artifacts["password_applied"] = bool(password_applied)

            if not saved_ok:
                return OperationResult(
                    success=False,
                    warnings=warnings,
                    changed_count=changed_count,
                    artifacts=artifacts,
                    error="문서 저장에 실패했습니다.",
                )

            if save_warning:
                if strict_password and password:
                    return OperationResult(
                        success=False,
                        warnings=warnings + [save_warning],
                        changed_count=changed_count,
                        artifacts=artifacts,
                        error=save_warning,
                    )
                warnings.append(save_warning)

            return OperationResult(
                success=True,
                warnings=warnings,
                changed_count=changed_count,
                artifacts=artifacts,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                warnings=warnings,
                changed_count=changed_count,
                artifacts=artifacts,
                error=str(e),
            )

    # ==================== 변환 기능 ====================

    def convert_to_pdf(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 PDF로 변환한다."""
        return self._convert(source_path, ConvertFormat.PDF, output_path)

    def convert_to_txt(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 TXT로 변환한다."""
        return self._convert(source_path, ConvertFormat.TXT, output_path)

    def convert_to_hwpx(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 HWPX로 변환한다."""
        return self._convert(source_path, ConvertFormat.HWPX, output_path)

    def convert_to_jpg(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 JPG로 변환한다. 첫 페이지만 저장한다."""
        return self._convert(source_path, ConvertFormat.JPG, output_path)

    def convert(
        self,
        source_path: str,
        target_format: ConvertFormat,
        output_path: Optional[str] = None,
    ) -> ConversionResult:
        """Worker에서 사용하는 공개 변환 API."""
        return self._convert(source_path, target_format, output_path)

    def _convert(
        self,
        source_path: str,
        target_format: ConvertFormat,
        output_path: Optional[str] = None
    ) -> ConversionResult:
        """단일 파일을 변환한다."""
        try:
            hwp = self._get_hwp()

            source = Path(source_path)
            if not source.exists():
                return ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"파일이 존재하지 않습니다: {source_path}"
                )

            # 출력 경로 결정
            if output_path is None:
                output_path = str(source.with_suffix(f".{target_format.value}"))

            # 파일 열기
            hwp.open(source_path)

            # 변환 형식 매핑
            format_map = {
                ConvertFormat.PDF: "PDF",
                ConvertFormat.TXT: "TEXT",
                ConvertFormat.HWPX: "HWPX",
                ConvertFormat.JPG: "JPEG",
                ConvertFormat.HTML: "HTML",
            }

            save_format = format_map.get(target_format, "PDF")
            hwp.save_as(output_path, format=save_format)

            return ConversionResult(
                success=True,
                source_path=source_path,
                output_path=output_path
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )

    def batch_convert(
        self,
        source_files: list[str],
        target_format: ConvertFormat,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        배치 변환

        Args:
            source_files: 변환할 파일 목록
            target_format: 목표 형식
            output_dir: 출력 폴더. None이면 원본 옆에 저장
            progress_callback: 진행 콜백 (current, total, filename)

        Returns:
            변환 결과 리스트
        """
        results: list[ConversionResult] = []
        total = len(source_files)

        try:
            hwp = self._get_hwp()

            for idx, source_path in enumerate(source_files):
                # 진행 콜백 호출
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)

                # 출력 경로 결정
                if output_dir:
                    from ..utils.output_paths import resolve_output_path

                    output_path = resolve_output_path(
                        output_dir,
                        source_path,
                        new_ext=target_format.value,
                    )
                else:
                    output_path = None

                # 파일 변환 실행
                result = self._convert(source_path, target_format, output_path)
                results.append(result)

                # 메모리 정리 (100건마다 GC)
                if (idx + 1) % 100 == 0:
                    gc.collect()

        except Exception as e:
            # 실패한 나머지 파일도 에러 결과로 채운다
            for remaining in source_files[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))

        return results

    # ==================== 병합 기능 ====================

    def merge_files(
        self,
        source_files: list[str],
        output_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ConversionResult:
        """
        여러 HWP 파일을 하나로 병합한다

        Args:
            source_files: 병합할 파일 목록 (순서대로)
            output_path: 출력 파일 경로
            progress_callback: 진행 콜백

        Returns:
            병합 결과
        """
        try:
            hwp = self._get_hwp()

            if len(source_files) < 2:
                return ConversionResult(
                    success=False,
                    source_path=str(source_files),
                    error_message="병합하려면 최소 2개 이상의 파일이 필요합니다."
                )

            total = len(source_files)

            # 첫 번째 파일 열기
            if progress_callback:
                progress_callback(1, total, Path(source_files[0]).name)
            hwp.open(source_files[0])

            # 나머지 파일 삽입
            for idx, file_path in enumerate(source_files[1:], start=2):
                if progress_callback:
                    progress_callback(idx, total, Path(file_path).name)

                # 문서 끝으로 이동
                hwp.Run("MoveDocEnd")
                # 페이지 나누기 삽입
                hwp.Run("BreakPage")
                # 파일 삽입 액션 실행
                hwp.Run("InsertFile")
                hwp.HParameterSet.HInsertFile.filename = file_path
                hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)

            # 결과 저장
            hwp.save_as(output_path)

            return ConversionResult(
                success=True,
                source_path=str(source_files),
                output_path=output_path
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=str(source_files),
                error_message=str(e)
            )

    # ==================== 분할 기능 ====================

    @staticmethod
    def parse_page_range(range_str: str, max_page: int) -> list[int]:
        """
        페이지 범위 문자열을 파싱한다

        Examples:
            "1-3" -> [1, 2, 3]
            "1,3,5" -> [1, 3, 5]
            "1-3,5,7-9" -> [1, 2, 3, 5, 7, 8, 9]

        Args:
            range_str: 페이지 범위 문자열
            max_page: 최대 페이지 수

        Returns:
            페이지 번호 리스트
        """
        pages: set[int] = set()

        # 공백 제거
        range_str = range_str.replace(" ", "")

        # 쉼표로 분리
        parts = range_str.split(",")

        for part in parts:
            if "-" in part:
                # 범위 처리
                match = re.match(r"(\d+)-(\d+)", part)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2))
                    for p in range(start, min(end + 1, max_page + 1)):
                        if p >= 1:
                            pages.add(p)
            else:
                # 단일 페이지
                try:
                    p = int(part)
                    if 1 <= p <= max_page:
                        pages.add(p)
                except ValueError:
                    logging.getLogger(__name__).debug(f"페이지 범위 파싱 무시: {part}")

        return sorted(pages)

    def split_file(
        self,
        source_path: str,
        page_ranges: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        HWP 파일을 페이지 범위별로 분할한다

        Args:
            source_path: 원본 파일 경로
            page_ranges: 페이지 범위 문자열 리스트 (예: ["1-3", "4-6"])
            output_dir: 출력 폴더
            progress_callback: 진행 콜백

        Returns:
            분할 결과 리스트
        """
        results: list[ConversionResult] = []

        try:
            hwp = self._get_hwp()

            source = Path(source_path)
            output_directory = Path(output_dir)
            output_directory.mkdir(parents=True, exist_ok=True)

            total = len(page_ranges)

            for idx, range_str in enumerate(page_ranges, start=1):
                if progress_callback:
                    progress_callback(idx, total, f"분할 {idx}/{total}")

                try:
                    # 원본 다시 열기
                    hwp.open(source_path)

                    # 전체 페이지 수 확인
                    total_pages = hwp.PageCount

                    # 페이지 범위 파싱
                    pages = self.parse_page_range(range_str, total_pages)

                    if not pages:
                        results.append(ConversionResult(
                            success=False,
                            source_path=source_path,
                            error_message=f"유효하지 않은 페이지 범위: {range_str}"
                        ))
                        continue

                    # 출력 파일명 생성
                    output_name = f"{source.stem}_p{pages[0]}-{pages[-1]}.hwp"
                    output_path = str(output_directory / output_name)

                    # 선택하지 않은 페이지를 역순으로 삭제한다
                    # pyhwpx가 페이지 삭제 API를 직접 제공하지 않아 순차 삭제로 처리한다
                    all_pages = set(range(1, total_pages + 1))
                    pages_to_delete = sorted(all_pages - set(pages), reverse=True)

                    for page in pages_to_delete:
                        # 해당 페이지로 이동해 페이지 전체를 선택한 뒤 삭제
                        try:
                            # 페이지 이동
                            hwp.Run("MoveDocBegin")
                            for _ in range(page - 1):
                                hwp.Run("MovePageDown")
                            # 페이지 선택 후 삭제
                            hwp.Run("MovePageBegin")
                            hwp.Run("MoveSelPageDown")
                            hwp.Run("Delete")
                        except Exception as del_e:
                            self._logger.warning(f"페이지 {page} 삭제 중 오류 (무시): {del_e}")
                            hwp.Run("Cancel")  # 선택 해제

                    # 결과 저장
                    hwp.save_as(output_path)

                    results.append(ConversionResult(
                        success=True,
                        source_path=source_path,
                        output_path=output_path
                    ))

                except Exception as inner_e:
                    results.append(ConversionResult(
                        success=False,
                        source_path=source_path,
                        error_message=str(inner_e)
                    ))

        except Exception as e:
            # 남은 범위는 동일한 오류로 채운다
            for remaining_range in page_ranges[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=str(e)
                ))

        return results

    # ==================== 데이터 주입 ====================

    def inject_data(
        self,
        template_path: str,
        data: dict[str, str],
        output_path: str
    ) -> ConversionResult:
        """
        HWP 템플릿에 데이터를 주입한다

        Args:
            template_path: 템플릿 파일 경로
            data: 필드명-값 매핑 딕셔너리
            output_path: 출력 경로

        Returns:
            주입 결과
        """
        result = self.fill_fields(
            source_path=template_path,
            values=data,
            output_path=output_path,
            ignore_missing=True,
        )
        return ConversionResult(
            success=result.success,
            source_path=template_path,
            output_path=output_path if result.success else None,
            error_message=result.error,
        )

    def batch_inject_data(
        self,
        template_path: str,
        data_list: list[dict[str, str]],
        output_dir: str,
        filename_field: Optional[str] = None,
        filename_template: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        배치 데이터 주입

        Args:
            template_path: 템플릿 파일 경로
            data_list: 데이터 리스트
            output_dir: 출력 폴더
            filename_field: 파일명으로 사용할 필드. None이면 순번 사용
            progress_callback: 진행 콜백

        Returns:
            주입 결과 리스트
        """
        results: list[ConversionResult] = []

        try:
            for result in self.iter_inject_data(
                template_path=template_path,
                data_iterable=data_list,
                output_dir=output_dir,
                filename_field=filename_field,
                filename_template=filename_template,
                progress_callback=progress_callback,
                total_count=len(data_list),
            ):
                results.append(result)

        except Exception as e:
            for _ in data_list[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=template_path,
                    error_message=str(e)
                ))

        return results

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
        """Streaming data-injection API to avoid loading all rows in memory."""
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        template = Path(template_path)
        try:
            total = int(total_count) if total_count is not None else len(data_iterable)  # type: ignore[arg-type]
        except Exception:
            total = -1

        if stats is not None:
            stats.setdefault("filename_collisions", 0)

        self._ensure_hwp()

        for idx, data in enumerate(data_iterable, start=1):
            if progress_callback:
                progress_callback(idx, total, f"생성 {idx}/{total if total > 0 else '?'}")

            from ..utils.filename_sanitizer import sanitize_filename

            if filename_template:
                rendered_name = self._render_filename_template(
                    template=filename_template,
                    row_data=data,
                    index=idx,
                    fallback_stem=template.stem,
                )
                safe_name = sanitize_filename(rendered_name)
                if not safe_name:
                    safe_name = f"{template.stem}_{idx:04d}"
                output_name = safe_name if safe_name.lower().endswith(".hwp") else f"{safe_name}.hwp"
            elif filename_field and filename_field in data:
                safe_name = sanitize_filename(str(data[filename_field]))
                if not safe_name:
                    safe_name = f"{template.stem}_{idx:04d}"
                output_name = f"{safe_name}.hwp"
            else:
                output_name = f"{template.stem}_{idx:04d}.hwp"

            output_path_obj = output_directory / output_name
            if output_path_obj.exists():
                if stats is not None:
                    stats["filename_collisions"] = int(stats.get("filename_collisions", 0)) + 1
                stem = output_path_obj.stem
                ext = output_path_obj.suffix
                for suffix_idx in range(1, 10_000):
                    candidate = output_directory / f"{stem}_{suffix_idx}{ext}"
                    if not candidate.exists():
                        output_path_obj = candidate
                        break

            output_path = str(output_path_obj)
            yield self.inject_data(template_path, data, output_path)

            if idx % 100 == 0:
                gc.collect()

    def clean_metadata(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict[str, Any]] = None
    ) -> ConversionResult:
        """
        문서 메타정보를 정리한다

        Args:
            source_path: 원본 파일 경로
            output_path: 출력 경로 (None이면 덮어쓰기)
            options: 정리 옵션
                - remove_author: 작성자/회사 정보 제거
                - remove_comments: 메모 제거
                - remove_tracking: 변경 추적 제거
                - set_distribution: 배포용 문서 설정

        Returns:
            정리 결과
        """
        result = self.harden_document(source_path=source_path, output_path=output_path, options=options)
        output = None
        if isinstance(result.artifacts, dict):
            maybe_output = result.artifacts.get("output_path")
            if maybe_output:
                output = str(maybe_output)
        return ConversionResult(
            success=result.success,
            source_path=source_path,
            output_path=output,
            error_message=result.error or ("\n".join(result.warnings) if result.warnings else None),
        )

