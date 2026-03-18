from __future__ import annotations

from typing import Any, Optional

from .fields import detect_pii_patterns, extract_text_for_scan
from .types import ConversionResult, OperationResult


def save_as_with_password(
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

    for kw in ("password", "passwd", "security_password"):
        try:
            hwp.save_as(output_path, **{kw: password_value})
            return True, True, None
        except TypeError:
            continue
        except Exception:
            continue

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

    hwp.save_as(output_path)
    return True, False, "암호 설정 API를 찾지 못해 암호 없이 저장했습니다."


def harden_document(
    handler: Any,
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
        hwp = handler._get_hwp()
        hwp.open(source_path)

        if bool(merged.get("scan_personal_info", False)):
            text = extract_text_for_scan(hwp)
            pii_counts, pii_samples, pii_total = detect_pii_patterns(
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
        saved_ok, password_applied, save_warning = save_as_with_password(
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


def clean_metadata(
    handler: Any,
    source_path: str,
    output_path: Optional[str] = None,
    options: Optional[dict[str, Any]] = None,
) -> ConversionResult:
    """문서 메타정보를 정리한다."""

    result = harden_document(handler, source_path=source_path, output_path=output_path, options=options)
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
