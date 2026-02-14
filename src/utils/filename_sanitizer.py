"""
Filename sanitization helpers (Windows-safe).

The app frequently derives output filenames from user-provided fields (e.g. Excel)
or source filenames. On Windows, a filename can be invalid due to reserved
characters, reserved device names, trailing spaces/dots, or excessive length.
"""

from __future__ import annotations

import re


_INVALID_CHARS_RE = re.compile(r'[<>:"/\\\\|?*]')
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f]")

# Windows reserved device names (case-insensitive), with or without extension.
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_filename(name: str, *, replacement: str = "_", max_length: int = 120) -> str:
    """
    Sanitize a filename (no directories) for Windows compatibility.

    - Replaces invalid characters and control chars.
    - Trims trailing spaces/dots.
    - Avoids reserved device names.
    - Ensures non-empty and length-limited result.
    """

    if not isinstance(name, str):
        name = str(name)

    # Normalize whitespace and remove surrounding spaces early.
    s = " ".join(name.strip().split())

    # Replace invalid / control characters.
    s = _CONTROL_CHARS_RE.sub(replacement, s)
    s = _INVALID_CHARS_RE.sub(replacement, s)

    # Windows disallows trailing space or dot in filenames.
    s = s.rstrip(" .")

    if not s:
        s = "output"

    # Avoid reserved device names.
    # Compare only the base part before the first dot (CON.txt is also invalid).
    base = s.split(".", 1)[0].upper()
    if base in _RESERVED_NAMES:
        s = f"{s}{replacement}"

    # Length guard (best-effort). Keep extension if present.
    if max_length > 0 and len(s) > max_length:
        if "." in s:
            stem, ext = s.rsplit(".", 1)
            # ext part length includes dot.
            ext_part = "." + ext
            keep = max(1, max_length - len(ext_part))
            s = stem[:keep].rstrip(" .") + ext_part
        else:
            s = s[:max_length].rstrip(" .")

    if not s:
        s = "output"

    return s

