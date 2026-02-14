"""
COM initialization helpers.

pyhwpx uses COM automation under the hood. Each worker thread should
initialize COM before interacting with HWP.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def com_context() -> Iterator[None]:
    """
    Initialize COM for the current thread if pythoncom is available.

    This is safe to use in environments where pythoncom is not installed;
    in that case it becomes a no-op.
    """

    pythoncom = None
    try:
        import pythoncom as _pythoncom  # type: ignore

        pythoncom = _pythoncom
    except Exception:
        pythoncom = None

    if pythoncom is None:
        yield
        return

    pythoncom.CoInitialize()
    try:
        yield
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            # Best-effort cleanup; avoid masking worker errors.
            pass

