from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _replace_path(temp_path: Path, target_path: Path) -> None:
    temp_path.replace(target_path)


def atomic_write_text(path: str | Path, content: str, *, encoding: str = "utf-8") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_path(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_bytes(path: str | Path, content: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_path(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: str | Path, payload: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=ensure_ascii, indent=indent),
    )
