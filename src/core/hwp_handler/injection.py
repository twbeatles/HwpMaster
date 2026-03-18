from __future__ import annotations

import gc
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional

from .types import ConversionResult, OperationResult


def render_filename_template(
    template: str,
    row_data: dict[str, str],
    index: int,
    fallback_stem: str,
) -> str:
    class _SafeDict(dict[str, str]):
        def __missing__(self, key: str) -> str:
            return ""

    data = {str(key): str(value) for key, value in (row_data or {}).items()}
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


def inject_data(
    handler: Any,
    template_path: str,
    data: dict[str, str],
    output_path: str,
) -> ConversionResult:
    """HWP 템플릿에 데이터를 주입한다."""

    result = handler.fill_fields(
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


def iter_inject_data(
    handler: Any,
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

    handler._ensure_hwp()

    for idx, data in enumerate(data_iterable, start=1):
        if progress_callback:
            progress_callback(idx, total, f"생성 {idx}/{total if total > 0 else '?'}")

        from ...utils.filename_sanitizer import sanitize_filename

        if filename_template:
            rendered_name = render_filename_template(
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
        yield handler.inject_data(template_path, data, output_path)

        if idx % 100 == 0:
            gc.collect()


def batch_inject_data(
    handler: Any,
    template_path: str,
    data_list: list[dict[str, str]],
    output_dir: str,
    filename_field: Optional[str] = None,
    filename_template: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[ConversionResult]:
    """배치 데이터 주입."""

    results: list[ConversionResult] = []

    try:
        for result in iter_inject_data(
            handler,
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
            results.append(
                ConversionResult(
                    success=False,
                    source_path=template_path,
                    error_message=str(e),
                )
            )

    return results


def mail_merge(
    handler: Any,
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
    """Mail-merge wrapper that returns a rich operation summary."""

    success_count = 0
    fail_count = 0
    warnings: list[str] = []
    outputs: list[str] = []
    failed_outputs: list[dict[str, str]] = []

    try:
        for idx, result in enumerate(
            iter_inject_data(
                handler,
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
