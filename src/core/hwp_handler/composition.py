from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Optional

from .types import ConversionResult


def merge_files(
    handler: Any,
    source_files: list[str],
    output_path: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> ConversionResult:
    """여러 HWP 파일을 하나로 병합한다."""

    try:
        hwp = handler._get_hwp()

        if len(source_files) < 2:
            return ConversionResult(
                success=False,
                source_path=str(source_files),
                error_message="병합하려면 최소 2개 이상의 파일이 필요합니다.",
            )

        total = len(source_files)

        if progress_callback:
            progress_callback(1, total, Path(source_files[0]).name)
        hwp.open(source_files[0])

        for idx, file_path in enumerate(source_files[1:], start=2):
            if progress_callback:
                progress_callback(idx, total, Path(file_path).name)

            hwp.Run("MoveDocEnd")
            hwp.Run("BreakPage")
            hwp.Run("InsertFile")
            hwp.HParameterSet.HInsertFile.filename = file_path
            hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)

        hwp.save_as(output_path)

        return ConversionResult(
            success=True,
            source_path=str(source_files),
            output_path=output_path,
        )
    except Exception as e:
        return ConversionResult(
            success=False,
            source_path=str(source_files),
            error_message=str(e),
        )


def parse_page_range(range_str: str, max_page: int) -> list[int]:
    """페이지 범위 문자열을 파싱한다."""

    pages: set[int] = set()
    range_str = range_str.replace(" ", "")
    parts = range_str.split(",")

    for part in parts:
        if "-" in part:
            match = re.match(r"(\d+)-(\d+)", part)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                for page in range(start, min(end + 1, max_page + 1)):
                    if page >= 1:
                        pages.add(page)
        else:
            try:
                page = int(part)
                if 1 <= page <= max_page:
                    pages.add(page)
            except ValueError:
                logging.getLogger(__name__).debug(f"페이지 범위 파싱 무시: {part}")

    return sorted(pages)


def split_file(
    handler: Any,
    source_path: str,
    page_ranges: list[str],
    output_dir: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[ConversionResult]:
    """HWP 파일을 페이지 범위별로 분할한다."""

    results: list[ConversionResult] = []

    try:
        hwp = handler._get_hwp()

        source = Path(source_path)
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        total = len(page_ranges)

        for idx, range_str in enumerate(page_ranges, start=1):
            if progress_callback:
                progress_callback(idx, total, f"분할 {idx}/{total}")

            try:
                hwp.open(source_path)

                total_pages = hwp.PageCount
                pages = parse_page_range(range_str, total_pages)

                if not pages:
                    results.append(
                        ConversionResult(
                            success=False,
                            source_path=source_path,
                            error_message=f"유효하지 않은 페이지 범위: {range_str}",
                        )
                    )
                    continue

                output_name = f"{source.stem}_p{pages[0]}-{pages[-1]}.hwp"
                output_path = str(output_directory / output_name)

                all_pages = set(range(1, total_pages + 1))
                pages_to_delete = sorted(all_pages - set(pages), reverse=True)

                for page in pages_to_delete:
                    try:
                        hwp.Run("MoveDocBegin")
                        for _ in range(page - 1):
                            hwp.Run("MovePageDown")
                        hwp.Run("MovePageBegin")
                        hwp.Run("MoveSelPageDown")
                        hwp.Run("Delete")
                    except Exception as del_e:
                        handler._logger.warning(f"페이지 {page} 삭제 중 오류 (무시): {del_e}")
                        hwp.Run("Cancel")

                hwp.save_as(output_path)

                results.append(
                    ConversionResult(
                        success=True,
                        source_path=source_path,
                        output_path=output_path,
                    )
                )
            except Exception as inner_e:
                results.append(
                    ConversionResult(
                        success=False,
                        source_path=source_path,
                        error_message=str(inner_e),
                    )
                )
    except Exception as e:
        for _ in page_ranges[len(results):]:
            results.append(
                ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=str(e),
                )
            )

    return results
