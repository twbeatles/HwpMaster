from __future__ import annotations

from .types import CapabilitySnapshot


def introspect_capabilities() -> CapabilitySnapshot:
    """Inspect pyhwpx capabilities without opening a document."""

    categories: dict[str, int] = {
        "file_io": 0,
        "field_form": 0,
        "find_replace": 0,
        "style_format": 0,
        "table": 0,
        "shape_graphic": 0,
        "security_privacy": 0,
        "automation_macro": 0,
        "navigation_selection": 0,
        "other": 0,
    }
    unsupported: list[str] = []

    try:
        import pyhwpx  # type: ignore

        names = sorted(name for name in dir(pyhwpx.Hwp) if not name.startswith("_"))

        for name in names:
            lowered = name.lower()
            if lowered.startswith(("file", "open", "save", "close", "quit")):
                categories["file_io"] += 1
            elif "field" in lowered or "metatag" in lowered or lowered.startswith("form"):
                categories["field_form"] += 1
            elif "find" in lowered or "replace" in lowered:
                categories["find_replace"] += 1
            elif "charshape" in lowered or "parashape" in lowered or "style" in lowered:
                categories["style_format"] += 1
            elif "table" in lowered or "cell" in lowered:
                categories["table"] += 1
            elif "shape" in lowered or "draw" in lowered or "picture" in lowered or "image" in lowered:
                categories["shape_graphic"] += 1
            elif (
                "private" in lowered
                or "encrypt" in lowered
                or "distribution" in lowered
                or "trackchange" in lowered
            ):
                categories["security_privacy"] += 1
            elif "macro" in lowered or "script" in lowered:
                categories["automation_macro"] += 1
            elif lowered.startswith(("move", "goto", "select")):
                categories["navigation_selection"] += 1
            else:
                categories["other"] += 1

        for key in ("security_privacy", "automation_macro", "field_form", "table", "shape_graphic"):
            if categories.get(key, 0) == 0:
                unsupported.append(key)

        return CapabilitySnapshot(
            pyhwpx_version=str(getattr(pyhwpx, "__version__", "unknown")),
            method_count=len(names),
            methods=names,
            action_count=sum(1 for name in names if name[:1].isupper()),
            actions=[name for name in names if name[:1].isupper()],
            categories=categories,
            unsupported_categories=unsupported,
        )
    except Exception:
        unsupported = [key for key in categories.keys() if key != "other"]
        return CapabilitySnapshot(
            pyhwpx_version="unknown",
            method_count=0,
            methods=[],
            action_count=0,
            actions=[],
            categories=categories,
            unsupported_categories=unsupported,
        )
