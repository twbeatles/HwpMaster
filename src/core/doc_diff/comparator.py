from __future__ import annotations

import difflib

from .models import ChangeType, DiffLine, DiffResult


def compare_lines(
    lines1: list[str],
    lines2: list[str],
    file1_path: str,
    file2_path: str,
) -> DiffResult:
    """
    SequenceMatcher 기반 라인 비교.

    - replace 구간은 (modified + added/deleted)로 분해해서 카운트를 더 정확히 산출합니다.
    """

    result = DiffResult(
        success=True,
        file1_path=file1_path,
        file2_path=file2_path,
        file1_lines=len(lines1),
        file2_lines=len(lines2),
    )

    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            for i in range(i1, i2):
                result.deleted_count += 1
                result.changes.append(
                    DiffLine(
                        line_number=i + 1,
                        change_type=ChangeType.DELETED,
                        original_text=lines1[i],
                    )
                )
            continue
        if tag == "insert":
            for j in range(j1, j2):
                result.added_count += 1
                result.changes.append(
                    DiffLine(
                        line_number=j + 1,
                        change_type=ChangeType.ADDED,
                        new_text=lines2[j],
                    )
                )
            continue

        old_len = i2 - i1
        new_len = j2 - j1
        paired = min(old_len, new_len)

        for k in range(paired):
            result.modified_count += 1
            result.changes.append(
                DiffLine(
                    line_number=i1 + k + 1,
                    change_type=ChangeType.MODIFIED,
                    original_text=lines1[i1 + k],
                    new_text=lines2[j1 + k],
                )
            )

        for i in range(i1 + paired, i2):
            result.deleted_count += 1
            result.changes.append(
                DiffLine(
                    line_number=i + 1,
                    change_type=ChangeType.DELETED,
                    original_text=lines1[i],
                )
            )

        for j in range(j1 + paired, j2):
            result.added_count += 1
            result.changes.append(
                DiffLine(
                    line_number=j + 1,
                    change_type=ChangeType.ADDED,
                    new_text=lines2[j],
                )
            )

    return result
