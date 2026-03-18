from __future__ import annotations

import re
from typing import Any, Optional

from .types import OperationResult


def extract_text_for_scan(hwp: Any) -> str:
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


def detect_pii_patterns(
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
            if not token or token in sample_values:
                continue
            sample_values.append(token)
            if len(sample_values) >= max(1, int(sample_limit)):
                break
        samples[key] = sample_values

    return counts, samples, total


def scan_personal_info(
    handler: Any,
    source_path: str,
    *,
    patterns: Optional[dict[str, str]] = None,
    sample_limit: int = 5,
) -> OperationResult:
    """Scan a document for personal-information patterns."""

    try:
        hwp = handler._get_hwp()
        hwp.open(source_path)
        text = extract_text_for_scan(hwp)
        if not text:
            return OperationResult(
                success=True,
                warnings=["문서 텍스트를 추출하지 못해 스캔 결과가 비어 있습니다."],
                changed_count=0,
                artifacts={"matches": {}, "samples": {}, "total": 0},
            )

        counts, samples, total = detect_pii_patterns(
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


def list_fields(handler: Any, source_path: str) -> OperationResult:
    """Return field names from a document."""

    warnings: list[str] = []
    try:
        hwp = handler._get_hwp()
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
            fields = [str(key).strip() for key in raw.keys() if str(key).strip()]
        elif isinstance(raw, (list, tuple, set)):
            fields = [str(item).strip() for item in raw if str(item).strip()]

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
    handler: Any,
    source_path: str,
    values: dict[str, Any],
    output_path: Optional[str] = None,
    *,
    ignore_missing: bool = True,
) -> OperationResult:
    """Fill field values in a document and save it."""

    warnings: list[str] = []
    updated_fields: list[str] = []
    missing_fields: list[str] = []

    try:
        hwp = handler._get_hwp()
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
