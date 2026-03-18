from __future__ import annotations

from typing import Any, Optional

from .types import OperationResult


def get_meta_tags(
    handler: Any,
    source_path: str,
    keys: Optional[list[str]] = None,
) -> OperationResult:
    """Read document meta tags (best effort across pyhwpx versions)."""

    warnings: list[str] = []
    tags: dict[str, str] = {}
    try:
        hwp = handler._get_hwp()
        hwp.open(source_path)

        key_list = [str(key) for key in (keys or []) if str(key).strip()]
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
                tags = {str(key): str(value) for key, value in raw.items()}
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
    handler: Any,
    source_path: str,
    tags: dict[str, Any],
    output_path: Optional[str] = None,
) -> OperationResult:
    """Set document meta tags (best effort across pyhwpx versions)."""

    warnings: list[str] = []
    updated: list[str] = []
    failed: list[str] = []

    try:
        hwp = handler._get_hwp()
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
