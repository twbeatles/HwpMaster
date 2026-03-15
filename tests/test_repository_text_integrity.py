from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCES = [PROJECT_ROOT / "main.py", *sorted((PROJECT_ROOT / "src").rglob("*.py"))]
MOJIBAKE_FRAGMENTS = (
    "\ufffd",
    "蹂묓빀",
    "遺꾪븷",
    "鍮꾧탳",
    "移섑솚",
    "異붿텧",
    "留곹겕",
    "留ㅽ겕",
    "臾몄꽌",
    "珥덇린",
    "諛섑솚",
    "寃곌낵",
)


def test_python_sources_are_utf8_decodable() -> None:
    unreadable: list[str] = []

    for path in PYTHON_SOURCES:
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            unreadable.append(f"{path.relative_to(PROJECT_ROOT)}: {exc}")

    assert not unreadable, "UTF-8 decoding failed:\n" + "\n".join(unreadable)


def test_python_sources_do_not_contain_known_mojibake_fragments() -> None:
    offenders: list[str] = []

    for path in PYTHON_SOURCES:
        text = path.read_text(encoding="utf-8")
        for fragment in MOJIBAKE_FRAGMENTS:
            if fragment in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {fragment}")

    assert not offenders, "Known mojibake fragments found:\n" + "\n".join(offenders)
