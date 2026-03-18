from __future__ import annotations

import gc
from pathlib import Path
from typing import Any, Callable, Optional

from .types import ConversionResult, ConvertFormat


def convert_document(
    handler: Any,
    source_path: str,
    target_format: ConvertFormat,
    output_path: Optional[str] = None,
) -> ConversionResult:
    """단일 파일을 변환한다."""

    try:
        hwp = handler._get_hwp()

        source = Path(source_path)
        if not source.exists():
            return ConversionResult(
                success=False,
                source_path=source_path,
                error_message=f"파일이 존재하지 않습니다: {source_path}",
            )

        if output_path is None:
            output_path = str(source.with_suffix(f".{target_format.value}"))

        hwp.open(source_path)

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
            output_path=output_path,
        )
    except Exception as e:
        return ConversionResult(
            success=False,
            source_path=source_path,
            error_message=str(e),
        )


def batch_convert(
    handler: Any,
    source_files: list[str],
    target_format: ConvertFormat,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[ConversionResult]:
    """배치 변환."""

    results: list[ConversionResult] = []
    total = len(source_files)

    try:
        handler._get_hwp()

        for idx, source_path in enumerate(source_files):
            if progress_callback:
                progress_callback(idx + 1, total, Path(source_path).name)

            if output_dir:
                from ...utils.output_paths import resolve_output_path

                output_path = resolve_output_path(
                    output_dir,
                    source_path,
                    new_ext=target_format.value,
                )
            else:
                output_path = None

            result = convert_document(handler, source_path, target_format, output_path)
            results.append(result)

            if (idx + 1) % 100 == 0:
                gc.collect()
    except Exception as e:
        for remaining in source_files[len(results):]:
            results.append(
                ConversionResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e),
                )
            )

    return results
