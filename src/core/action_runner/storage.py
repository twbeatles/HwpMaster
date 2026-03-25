from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from ...utils.atomic_write import atomic_write_text
from .models import ActionCommand, ActionTemplate


def load_templates(runner: Any) -> None:
    if not runner._template_file.exists():
        return
    try:
        raw = json.loads(runner._template_file.read_text(encoding="utf-8"))
        runner._templates = {}
        for item in raw.get("templates", []):
            tpl = ActionTemplate.from_dict(item)
            if tpl.name:
                runner._templates[tpl.name] = tpl
    except Exception as e:
        runner._logger.warning(f"액션 템플릿 로드 실패: {e}")
        runner._templates = {}


def save_templates(runner: Any) -> None:
    payload = {"version": "1.0", "templates": [tpl.to_dict() for tpl in runner._templates.values()]}
    atomic_write_text(
        runner._template_file,
        json.dumps(payload, ensure_ascii=False, indent=2),
    )


def list_templates(runner: Any) -> list[ActionTemplate]:
    return list(runner._templates.values())


def get_template(runner: Any, name: str) -> Optional[ActionTemplate]:
    return runner._templates.get(name)


def save_template(
    runner: Any,
    name: str,
    commands: list[ActionCommand],
    description: str = "",
) -> bool:
    template_name = str(name or "").strip()
    if not template_name:
        return False
    normalized = [cmd.normalize() for cmd in commands]
    now = datetime.now().isoformat()
    existing = runner._templates.get(template_name)
    created_at = existing.created_at if existing is not None else now
    runner._templates[template_name] = ActionTemplate(
        name=template_name,
        description=description,
        created_at=created_at,
        updated_at=now,
        commands=normalized,
    )
    save_templates(runner)
    return True


def delete_template(runner: Any, name: str) -> bool:
    if name in runner._templates:
        del runner._templates[name]
        save_templates(runner)
        return True
    return False
