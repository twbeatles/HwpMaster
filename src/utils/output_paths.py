"""
Output path helpers.

Policy: default to writing results to an output directory and avoid overwriting
existing files by appending an incrementing suffix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .filename_sanitizer import sanitize_filename


def ensure_dir(path: str) -> str:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def _with_suffix(original: Path, new_ext: Optional[str]) -> Path:
    if not new_ext:
        return original
    ext = new_ext
    if not ext.startswith("."):
        ext = "." + ext
    return original.with_suffix(ext)


def resolve_output_path(
    output_dir: str,
    src_path: str,
    *,
    new_ext: Optional[str] = None,
    suffix: Optional[str] = None,
) -> str:
    """
    Create a collision-free output path in output_dir for src_path.

    - new_ext: extension without dot (e.g. "pdf") or with dot (".pdf")
    - suffix: inserted before extension (e.g. "_cleaned")
    """

    out_dir = Path(ensure_dir(output_dir))
    src = Path(src_path)

    base = sanitize_filename(src.stem)
    if suffix:
        base = sanitize_filename(f"{base}{suffix}")

    candidate = _with_suffix(out_dir / base, new_ext or src.suffix)
    if not candidate.exists():
        return str(candidate)

    # Collision: append _1, _2, ...
    for i in range(1, 10_000):
        cand = _with_suffix(out_dir / f"{base}_{i}", new_ext or src.suffix)
        if not cand.exists():
            return str(cand)

    raise RuntimeError("출력 파일 경로를 생성할 수 없습니다 (충돌이 너무 많음).")
